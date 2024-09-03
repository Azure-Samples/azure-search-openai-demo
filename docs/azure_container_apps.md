# Deploying on Azure Container Apps
Due to [a limitation](https://github.com/Azure/azure-dev/issues/2736) of azd, the azure.yaml file lives in folder `aca-host` along with symbolic links to `app`,`data` and `scripts` folder.
## For Linux/MacOS users
If you are on Linux/MacOS, it should work without any extra settings to deploy on Azure Container Apps. Please use:
```bash
cd aca-host
azd up
```
## For windows users
Because windows allow symbolic links by default, you may need to enbale [Developer Mode](https://learn.microsoft.com/en-us/windows/apps/get-started/enable-your-device-for-development),
and enable symlinks for git before cloning this repo. 
To enable symlinks for git, please use
```
# local setting
git config core.symlinks true
# Alternatively, enable symlinks globally
git config --global core.symlinks true
```

For more info please check [here](https://stackoverflow.com/questions/5917249/git-symbolic-links-in-windows).