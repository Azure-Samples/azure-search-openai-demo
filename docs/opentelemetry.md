
## Starting the Aspire Dashboard

The .NET Aspire dashboard is an OpenTelemetry dashboard service that can be run locally using Docker. The dashboard is a web application that can be accessed at `http://localhost:18888`.

You can set a temporary key for OTLP API as an environment variable when starting the container. The key is used to verify that incoming data is from a trusted source. The key is used to authenticate the data source and is not used to authenticate users accessing the dashboard.

```console
set OTLP_KEY=f142d227-486e-4e80-b7bd-3446e6aa8ea1  # Your own unique key
docker run --rm -it -p 18888:18888 -p 4317:18889 --name aspire-dashboard \
  -e DASHBOARD__OTLP__AUTHMODE='ApiKey' \
  -e DASHBOARD__OTLP__PRIMARYAPIKEY='${OTLP_KEY}' \
  mcr.microsoft.com/dotnet/nightly/aspire-dashboard:8.0-preview
```

Once you have started the container, look at the output for a link to the dashboard, the service generates a unique sign-in key that you can use to access the dashboard and prints this to stdout.

## Starting the service with OpenTelemetry

To send data to the Aspire dashboard, you need to configure your application to send data to the OpenTelemetry collector. The collector is a service that receives telemetry data from your application and forwards it to the dashboard.

