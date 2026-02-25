
package observability

import (
	"log/slog"
	"os"
)


func SetupLogger(level slog.Level) *slog.Logger {
	handler := slog.NewJSONHandler(os.Stdout, &slog.HandlerOptions{
		Level:       level,
		AddSource:   true, 
		ReplaceAttr: nil,
	})

	logger := slog.New(handler)
	slog.SetDefault(logger) 
	return logger
}

func WithContext(logger *slog.Logger, attrs ...any) *slog.Logger {
	return logger.With(attrs...)
}

func Info(msg string, args ...any) {
	slog.Info(msg, args...)
}

func Error(msg string, args ...any) {
	slog.Error(msg, args...)
}
