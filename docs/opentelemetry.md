# OpenTelemetry support

This project has instrumentation for OpenTelemetry. The OpenTelemetry project provides a single set of APIs, libraries, agents, and instrumentation resources to capture distributed traces and metrics from your application. There are two supported options for viewing traces emitted by this application:

1. Locally using [the .NET Aspire Dashboard](#starting-the-aspire-dashboard)
2. Remotely using [Azure Monitor and Application Insights](../README.md#monitoring-with-application-insights)

## Starting the .NET Aspire Dashboard

The .NET Aspire dashboard is an OpenTelemetry dashboard service that can be run locally using Docker. The dashboard is a web application that can be accessed at `http://localhost:18888`. The .NET Aspire Dashboard is designed for local development and testing. Once the container is stopped, any traces, logs and metrics will be destroyed. For persistent logging, see the [Azure Monitor and Application Insights](../README.md#monitoring-with-application-insights) integration.

You can set a temporary key for OTLP API as an environment variable when starting the container. The key is used to verify that incoming data is from a trusted source. The key is used to authenticate the data source and is not used to authenticate users accessing the dashboard.

```console
export OTLP_KEY=f142d227-486e-4e80-b7bd-3446e6aa8ea1  # Your own unique key
docker run --rm -it -p 18888:18888 -p 4317:18889 --name aspire-dashboard \
  -e DASHBOARD__OTLP__AUTHMODE='ApiKey' \
  -e DASHBOARD__OTLP__PRIMARYAPIKEY='${OTLP_KEY}' \
  mcr.microsoft.com/dotnet/nightly/aspire-dashboard:8.0-preview
```

Once you have started the container, look at the output for a link to the dashboard, the service generates a unique sign-in key that you can use to access the dashboard and prints this to stdout.

## Starting the service with OpenTelemetry

To send data to the Aspire dashboard, you need to configure your application to send data to the OpenTelemetry collector. The collector is a service that receives telemetry data from your application and forwards it to the dashboard.

From the `app/` directory, you can start the service with the following command and additional environment variables:

```console
$ OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317 OTEL_EXPORTER_OTLP_TRACES_API_KEY=${OTLP_KEY}  ./start.sh
```

This will launch the web services and connect all tracing to the OTLP endpoint running in the dashboard container.
