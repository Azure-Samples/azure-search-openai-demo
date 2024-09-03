# Deploying on Azure Container Apps

Due to [a limitation](https://github.com/Azure/azure-dev/issues/2736) of azd, the azure.yaml file for deploying to Azure Container Apps lives here along with symbolic links to `app`,`data` and `scripts` folder.

## For Linux/MacOS users

If you are on Linux/MacOS, it should work without any extra settings to deploy to Azure Container Apps. Please use:

```bash
cd aca-host
azd up
```

## For Windows users

Because Windows [doesn't enable symbolic links by default](https://stackoverflow.com/questions/5917249/git-symbolic-links-in-windows), you may need to enable [Developer Mode](https://learn.microsoft.com/windows/apps/get-started/enable-your-device-for-development) and symlinks for git before cloning this repo.
To enable symlinks for git, please use

```bash
# local setting
git config core.symlinks true
# Alternatively, enable symlinks globally
git config --global core.symlinks true
```

Please ensure that the symlinks work correctly and then run:

```bash
cd aca-host
azd up
```
