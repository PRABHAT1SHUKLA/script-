// tracing.go
package observability

import (
	"context"
	"log/slog"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/propagation"
	sdkresource "go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

// InitTracing sets up OTLP exporter → Jaeger/Tempo/any OTLP backend
// Endpoint example: "http://localhost:4318" or collector service
func InitTracing(serviceName string, otlpEndpoint string) error {
	ctx := context.Background()

	exporter, err := otlptracehttp.New(ctx,
		otlptracehttp.WithEndpoint(otlpEndpoint),
		otlptracehttp.WithInsecure(), // use TLS in prod
	)
	if err != nil {
		return err
	}

	res, err := sdkresource.New(ctx,
		sdkresource.WithAttributes(
			semconv.ServiceName(serviceName),
			// add env, version, etc.
		),
	)
	if err != nil {
		return err
	}

	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
		sdktrace.WithSampler(sdktrace.AlwaysSample()), // change to ParentBased(TraceIDRatioBased(0.1)) in prod
	)

	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(
		propagation.TraceContext{},
		propagation.Baggage{},
	))

	slog.Info("OpenTelemetry tracing initialized", "service", serviceName, "endpoint", otlpEndpoint)
	return nil
}

func StartSpan(ctx context.Context, name string, opts ...trace.SpanStartOption) (context.Context, trace.Span) {
	return otel.Tracer("github.com/yourorg/yourrepo").Start(ctx, name, opts...)
}

/
func SpanSetUserID(ctx context.Context, userID string) {
	if span := trace.SpanFromContext(ctx); span.IsRecording() {
		span.SetAttributes(attribute.String("user.id", userID))
	}
}
