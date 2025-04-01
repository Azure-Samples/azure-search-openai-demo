# Potential error messages when Deploying the template locally

This section covers common error messages you might encounter when deploying templates locally, along with solutions to resolve them.

## Error message: Quota and resources available: InsufficientQuota:
 _This operation require 30 new capacities in quota Tokens Per Minute (thousands) - GPT-35-Turbo, which is bigger than the current available capacity 0. The current quota usage is 30 and the quota limit is 30 for quota Tokens Per Minute (thousands) - GPT-35-Turbo._

Possible solutions: 

1.	Review and adjust the quota: Check if you can increase the quota for Tokens Per Minute (thousands) for your gpt-model in your Azure settings. This might involve requesting a quota increase through the Azure portal.
2.	Optimize token usage: Examine your implementation to see if you can reduce the number of tokens you're using. 
3.	Contact Azure support: If you can't adjust the quota yourself, reach out to Azure support with the tracking ID for specific assistance with your issue.

## MaxNumberofGlobalEnviromentsInSubExceeded: The subscription ID cannot have more than 2 container app environments.
Possible solutions:

1. Delete Existing Environments: Check if there are any container app environments you no longer need and delete them to free up space.

2. Request a Quota Increase: Request an increase in the limit of container app environments. You can do this through the Azure portal by clicking the help icon (question mark) in the top right corner and creating a support ticket.

3. Review Subscription Configuration: Ensure your subscription is configured correctly and that there are no additional restrictions causing the issue.

4. Use Different Regions: If possible, try creating the environments in different regions to avoid the global limit.


## Cargo, the Rust package manager, is not installed or is not on Path.

_This package requires Rust and Cargo to compile extensions. Install it through the system's package manager._

Possible solution: 
1. If Rust and Cargo are not installed, you can install them using the Rustup toolchain installer. This will set up the necessary tools and add them to your PATH.
