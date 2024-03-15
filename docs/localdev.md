# Local development of Chat App

You can only run locally **after** having successfully run the `azd up` command. If you haven't yet, follow the steps in [Azure deployment](../README.md#azure-deployment) above.

1. Run `azd auth login`
2. Change dir to `app`
3. Run `./start.ps1` or `./start.sh` or run the "VS Code Task: Start App" to start the project locally.

## Hot reloading frontend and backend files

When you run `./start.ps1` or `./start.sh`, the backend files will be watched and reloaded automatically. However, the frontend files will not be watched and reloaded automatically.

To enable hot reloading of frontend files, open a new terminal and navigate to the frontend directory:

```shell
cd app/frontend
```

Then run:

```shell
npm run dev
```

You should see:

```shell
> frontend@0.0.0 dev
> vite


  VITE v4.5.1  ready in 957 ms

  ➜  Local:   http://localhost:5173/
  ➜  Network: use --host to expose
  ➜  press h to show help
```

Navigate to the URL shown in the terminal (in this case, `http://localhost:5173/`).  This local server will watch and reload frontend files. All backend requests will be routed to the Python server according to `vite.config.ts`.

Then, whenever you make changes to frontend files, the changes will be automatically reloaded, without any browser refresh needed.


## Using a local OpenAI-compatible API

You may want to save costs by developing against a local LLM server, such as
[llamafile](https://github.com/Mozilla-Ocho/llamafile/). Note that a local LLM
will generally be slower and not as sophisticated.

Once you've got your local LLM running and serving an OpenAI-compatible endpoint, set these environment variables:

```shell
azd env set OPENAI_HOST local
azd env set OPENAI_BASE_URL <your local endpoint>
```

For example, to point at a local llamafile server running on its default port:

```shell
azd env set OPENAI_BASE_URL http://localhost:8080/v1
```

If you're running inside a dev container, use this local URL instead:

```shell
azd env set OPENAI_BASE_URL http://host.docker.internal:8080/v1
```
