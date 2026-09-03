# 09 · OpenTelemetry: Traces From Any Language

> ← [`08-langchain-and-langgraph.md`](08-langchain-and-langgraph.md) · **Next:** [`10-scores-and-user-feedback.md`](10-scores-and-user-feedback.md) →

---

This is LangFuse's most architecturally distinctive capability, and it has no LangSmith equivalent.

> **LangFuse operates as an OpenTelemetry backend.** It receives OTLP on a public endpoint and maps incoming OTel spans onto its own data model — traces, observations, scores.

Which means: **anything that can emit OpenTelemetry can send traces to LangFuse.** No LangFuse SDK required, in any language.

---

## 1. Why this matters

Two situations, both common, that a callback-based tracer cannot address at all.

### Your LLM code isn't Python or TypeScript

LLM features increasingly live inside existing services, and those services are written in whatever the team already used:

```
Go API gateway ──► calls an LLM for classification
Java backend   ──► RAG over an internal corpus
Rust service   ──► embedding + vector search
.NET app       ──► summarisation endpoint
```

None of these has a LangFuse SDK. All of them have a mature OpenTelemetry SDK. So they can all send traces.

### You already run OpenTelemetry

If your platform team runs OTel collectors, LLM tracing becomes **one more signal in an existing pipeline** rather than a parallel stack with its own agent, its own config and its own gaps. You can fan out — LLM spans to LangFuse, everything to your general APM — from a collector you already operate.

> **This is the difference between an observability tool that fits your infrastructure and one that sits beside it.** For a small team the distinction is academic. For a platform team with an existing tracing standard, it decides the tool.

---

## 2. The endpoint

Traces are received at `/api/public/otel`:

| Instance | OTLP endpoint |
|---|---|
| EU (default) | `https://cloud.langfuse.com/api/public/otel` |
| US | `https://us.cloud.langfuse.com/api/public/otel` |
| Japan | `https://jp.cloud.langfuse.com/api/public/otel` |
| HIPAA | `https://hipaa.cloud.langfuse.com/api/public/otel` |
| **Self-hosted** | `http://localhost:3000/api/public/otel` *(v3.22.0+)* |

**Protocols:** OTLP over HTTP, both `HTTP/JSON` and `HTTP/protobuf`.

> **gRPC is not currently supported.** Worth knowing early, because OTLP/gRPC is a very common default in existing OTel setups — several SDKs and collector configs use it unless told otherwise. If your exporter is silently failing, this is the first thing to check.

---

## 3. Authentication

Basic auth with your key pair, base64-encoded:

```bash
echo -n "pk-lf-1234567890:sk-lf-1234567890" | base64
```

> On GNU systems, add `-w 0` for long keys — otherwise `base64` wraps the output at 76 characters and you get an invalid header that fails in a way that does not mention line wrapping.

Then configure any OTel SDK by environment:

```bash
OTEL_EXPORTER_OTLP_ENDPOINT="https://cloud.langfuse.com/api/public/otel"
OTEL_EXPORTER_OTLP_HEADERS="Authorization=Basic ${AUTH_STRING},x-langfuse-ingestion-version=4"
```

Or signal-specific, if you already export other signals elsewhere:

```bash
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="https://cloud.langfuse.com/api/public/otel/v1/traces"
OTEL_EXPORTER_OTLP_TRACES_HEADERS="Authorization=Basic ${AUTH_STRING},x-langfuse-ingestion-version=4"
```

**The signal-specific form is usually what you want in a real deployment**, because it lets traces go to LangFuse while metrics and logs continue to your existing backend. The generic `OTEL_EXPORTER_OTLP_ENDPOINT` redirects everything.

> **Note `x-langfuse-ingestion-version=4`.** This pins the ingestion contract. Since it is a version pin, treat it as something to verify against current docs rather than copy forever — the docs I read specify 4 for the current SDK line.

---

## 4. A worked example — Go

Nothing LangFuse-specific in the code; the wiring is entirely environment:

```bash
export AUTH=$(echo -n "pk-lf-...:sk-lf-..." | base64 -w 0)
export OTEL_EXPORTER_OTLP_TRACES_ENDPOINT="https://cloud.langfuse.com/api/public/otel/v1/traces"
export OTEL_EXPORTER_OTLP_TRACES_HEADERS="Authorization=Basic ${AUTH},x-langfuse-ingestion-version=4"
export OTEL_EXPORTER_OTLP_PROTOCOL="http/protobuf"
```

```go
package main

import (
    "context"
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
    "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
    sdktrace "go.opentelemetry.io/otel/sdk/trace"
)

func initTracer(ctx context.Context) (*sdktrace.TracerProvider, error) {
    exp, err := otlptracehttp.New(ctx)      // reads the OTEL_* env vars
    if err != nil {
        return nil, err
    }
    tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exp))
    otel.SetTracerProvider(tp)
    return tp, nil
}

func classify(ctx context.Context, text string) (string, error) {
    tracer := otel.Tracer("classifier")

    ctx, span := tracer.Start(ctx, "classify_ticket")
    defer span.End()
    span.SetAttributes(attribute.String("langfuse.session.id", sessionID))

    ctx, gen := tracer.Start(ctx, "llm_call")
    gen.SetAttributes(
        attribute.String("gen_ai.request.model", "gpt-4o-mini"),
        attribute.Int("gen_ai.usage.input_tokens", inTok),
        attribute.Int("gen_ai.usage.output_tokens", outTok),
    )
    label, err := callModel(ctx, text)
    gen.End()

    return label, err
}
```

```go
// flush before exit — same requirement as lesson 03 §5
defer tp.Shutdown(context.Background())
```

> **The attribute names are the part to get right, and the part I will not assert precisely.** LangFuse maps incoming OTel attributes onto its data model, and it understands the **OpenTelemetry GenAI semantic conventions** (`gen_ai.*`) plus LangFuse-specific attributes for things like session and user. Which exact keys map to `generation` type, token counts, `session_id` and `user_id` is version-dependent and precisely the kind of detail that changes.
>
> **Check the OpenTelemetry integration page for the current attribute mapping** before relying on it. The pattern above is the right *shape*; verify the keys. Getting this wrong produces spans that arrive and render as generic work — no tokens, no cost, no session grouping — which looks like the integration failing when it is actually an attribute-name mismatch.

---

## 5. Via a collector — the production shape

For a real deployment, export to a collector rather than pointing every service at LangFuse directly:

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:                       # services can speak gRPC to the COLLECTOR
      http:

processors:
  batch:
  # drop or redact payload attributes before they leave your network — lesson 13
  attributes/redact:
    actions:
      - key: gen_ai.prompt
        action: delete

exporters:
  otlphttp/langfuse:              # collector → LangFuse must be HTTP, not gRPC
    endpoint: https://cloud.langfuse.com/api/public/otel
    headers:
      Authorization: "Basic ${env:LANGFUSE_AUTH}"
      x-langfuse-ingestion-version: "4"
  otlp/datadog:
    endpoint: ...

service:
  pipelines:
    traces/llm:
      receivers:  [otlp]
      processors: [batch, attributes/redact]
      exporters:  [otlphttp/langfuse, otlp/datadog]
```

Three real advantages, and the first is the big one:

| Advantage | Why it matters |
|---|---|
| **The collector can speak gRPC to your services** even though LangFuse needs HTTP | Removes the §2 constraint from every service — one translation point instead of N |
| **Redaction happens centrally** | One `attributes/redact` processor covers every service in every language. Compare doing it per-SDK in five languages |
| **Fan-out** | LLM spans to LangFuse *and* everything to your APM, from one pipeline |
| Sampling and batching centrally | Consistent policy rather than per-service configuration drift |

> **The redaction point is the one to notice**, and it connects directly to lesson 13. A collector processor is the only place you can enforce "no prompt text leaves this network" across a polyglot fleet. Per-SDK masking means five implementations and five chances to miss one.

---

## 6. The honest limits

Not a free lunch, and worth knowing before you plan on it.

| Limit | Consequence |
|---|---|
| **No gRPC to LangFuse** | Requires HTTP export, or a collector to translate |
| **Attribute mapping is a contract you must learn** | Send generic spans and you get generic observations — no tokens, no cost, no session |
| **No `@observe` ergonomics** | You write span lifecycles by hand in Go/Java/Rust. The Python SDK's convenience is real and you give it up |
| **Scores need the API, not OTel** | Lesson 10's scoring goes through the LangFuse API/SDK. OTel carries traces, not evaluations |
| **Version-pinned header** | `x-langfuse-ingestion-version` means the ingestion contract can move under you |

> **So the realistic split for a polyglot org:** Python and TypeScript services use the LangFuse SDK and get `@observe`, `propagate_attributes` and scoring for free. Other languages export OTel spans and get *tracing* — with scoring done from a small service or job that calls the API. That is a good outcome and it is not the same as full parity, and it is better to know that going in than to discover it when someone asks why the Go service has no feedback scores.

---

## Recap

- **LangFuse is an OTLP backend** — `/api/public/otel`, Basic auth with base64 `public:secret`, HTTP/JSON or HTTP/protobuf.
- **No gRPC to LangFuse.** Very common default elsewhere; first thing to check when an exporter silently fails.
- Configure any OTel SDK by environment; prefer the **signal-specific** vars so other signals keep their existing destination.
- **This is what LangSmith cannot do:** traces from Go, Java, Rust, .NET — any OTel language, no LangFuse SDK.
- **Attribute names are the contract.** Wrong keys → spans arrive as generic work with no tokens, cost or session. Verify against current docs.
- **A collector is the production shape**: translates gRPC→HTTP, redacts centrally across a polyglot fleet, and fans out to LangFuse plus your APM.
- Limits: no `@observe` ergonomics outside Python/TS, and **scores go through the API, not OTel**.

---

## Self-check

1. Your Go service's OTel exporter reports success and nothing appears in LangFuse. Two things to check first?
2. Spans arrive but show no tokens or cost. What's wrong, and where do you look it up?
3. Give the strongest argument for a collector rather than direct export, for a five-language fleet.
4. What does a Go service *not* get, compared with a Python one, and how would you close that gap?

---

**Next:** [`10-scores-and-user-feedback.md`](10-scores-and-user-feedback.md) →
