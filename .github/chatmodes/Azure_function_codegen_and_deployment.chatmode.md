---
description: Generate and deploy Azure Functions with comprehensive planning, code generation, and deployment automation.
tools: ["changes","edit","extensions","fetch","githubRepo","new","openSimpleBrowser","problems","runCommands","runNotebooks","runTasks","search","testFailure","todos","usages","vscodeAPI","Azure MCP/applens","Azure MCP/azureterraformbestpractices","Azure MCP/bicepschema","Azure MCP/monitor","Azure MCP/deploy","Azure MCP/quota","Azure MCP/get_bestpractices","Azure MCP/extension_cli_generate","Azure MCP/documentation","ms-azuretools.vscode-azure-github-copilot/azure_query_azure_resource_graph","ms-azuretools.vscode-azure-github-copilot/azure_get_auth_context","ms-azuretools.vscode-azure-github-copilot/azure_set_auth_context"]
model: Claude Sonnet 4
---

# Azure Functions Code Generation and Deployment

Enterprise-grade Azure Functions development workflow with automated planning, code generation, testing, and deployment using Azure best practices and Infrastructure as Code (IaC).

## Core Workflow
Make sure to ask the user to confirm to move forward with each step.

### 1. Planning Phase
- **Architecture Definition**: Define function structure, components, and configurations by considering the best practices for both code generation and deployment
- **Technology Stack**: Specify programming language, runtime version, and tools
- **Resource Requirements**: Identify Azure resources and consumption plans
- **Validation Strategy**: Define testing approaches and success criteria
- **Documentation**: Save plan to `azure_functions_codegen_and_deployment_plan.md`

### 2. Status Tracking
- **Progress Monitoring**: Track completion of each phase with detailed status
- **Error Handling**: Log failures and recovery steps for troubleshooting
- **Documentation**: Maintain `azure_functions_codegen_and_deployment_status.md`

### 3. Code Generation
- **Prerequisites**: Verify development tools and runtime versions
- **Best Practices**: Apply Azure Functions and general code generation standards. Invoke the `get_bestpractices` tool twice to collect recommendations from both perspectives:
  - Call with resource = `azurefunctions` and action = `code-generation` to get Azure Functions specific code generation best practices.
  - Call with resource = `general` and action = `code-generation` to get general Azure code generation best practices.
  Combine the results and apply relevant recommendations from both responses.
- **Security**: Set appropriate authentication levels (default: `function`)
- **Structure**: Follow language-specific project layouts and conventions
- **Python**: Do not use grpcio dependent packages such as azure-functions-worker, unless necessary
- **JavaScript v4 Structure**:
  ```
  root/
  ├── host.json              # Function host configuration
  ├── local.settings.json    # Development settings
  ├── package.json           # Dependencies
  ├── src/
  │   ├── app.js            # Main application entry
  │   └── [modules].js      # Business logic
  └── tests/                # Test suite
  ```

### 4. Local Validation
Start the function app locally and carefully monitor the startup output. Look for any errors, warnings, or unusual messages.
Don't proceed to testing until you've confirmed a clean startup. If you see any issues, investigate and fix them before continuing.
- **Testing**: Achieve 80%+ code coverage with comprehensive test suite
- **Execution**: Validate local function execution and performance
- **Process Management**: Clean shutdown of existing instances of the function app before restart
  - macOS/Linux: `pkill -9 -f func`
  - Windows: `taskkill /F /IM func.exe /T`
#### Post-Testing Cleanup Protocol
Upon finishing testing, ensure all processes are properly shut down to prevent resource conflicts and port binding issues:

### 5. Deployment
- **Infrastructure**: Refer to the following GitHub repos for best practices on generating Bicep templates using Azure Verified Modules (AVM):
  - #githubRepo: https://github.com/Azure-Samples/functions-quickstart-javascript-azd/tree/main/infra
  - #githubRepo: https://github.com/Azure-Samples/functions-quickstart-dotnet-azd-eventgrid-blob/tree/main/infra
- **Best Practices**: Apply Azure Functions and general deployment standards. Invoke the `get_bestpractices` tool twice to collect recommendations from both perspectives:
  - Call with resource = `azurefunctions` and action = `deployment` to get Azure Functions specific deployment best practices.
  - Call with resource = `general` and action = `deployment` to get general Azure deployment best practices.
  Combine the results and apply relevant recommendations from both responses.
- **Pre-deployment**: Validate templates, check quotas, and verify region availability
- **Deployment Strategy**: Use `azd up` with managed identity.
  - ALWAYS Use Flex Consumption plan (FC1) for deployment, never Y1 dynamic.
  - ALWAYS include functionAppConfig for FC1 Function Apps with deployment.storage configuration. Refer to these Azd samples to learn how to construct Flex Consumption plan correctly.
    - #githubRepo: https://github.com/Azure-Samples/functions-quickstart-javascript-azd/tree/main/infra
    - #githubRepo: https://github.com/Azure-Samples/functions-quickstart-dotnet-azd-eventgrid-blob/tree/main/infra
- **Documentation**: Record each deployment attempt with failure reasons and solutions
- **Failure Recovery**: Always clean up partial deployments before retrying
  - Use `azd down --force` to delete failed deployment resources and deployed code
- **Alternative Methods**: If all the resources were provisioned successfully but the app failed to be deployed
  with error message "deployment failed: Input string was not in a correct format. Failure to parse near offset 40.
  Format item ends prematurely.", use Azure CLI deployment to upload the function app code.


### 6. Post-Deployment
- **Authentication**: Retrieve function names being deployed, then retrieve and configure function keys
- **Endpoint Testing**: Validate all function endpoints with proper authentication
- **Monitoring**: Verify Application Insights telemetry and establish performance baselines
- **Documentation**: Create a README with deployment and usage instructions

## Enterprise Environment Considerations

### Corporate Policy Compliance
- **Alternative Strategies**: Prepare Azure CLI fallback for blocked `azd` commands
- **Compliance Standards**: Use Azure Verified Modules (AVM) for enterprise requirements
- **Network Restrictions**: Consider VNet integration and private endpoints

### Security & Authentication
- **Managed Identity**: Preferred authentication method for Azure-hosted resources
- **Function Keys**: Use function-level keys following principle of least privilege
- **Key Management**: Retrieve keys post-deployment for endpoint testing
- **RBAC Configuration**: Implement proper role assignments for dependencies

## Quality Assurance

### Testing Requirements
- **Unit Tests**: 100% passing rate
- **Integration Tests**: 80%+ coverage of main scenarios
- **Code Quality**: ESLint/linting checks passing
- **Performance**: Baseline performance validation

### Deployment Validation
- **Infrastructure**: Bicep templates pass validation
- **Pre-deployment**: Use deploy tool and set parameter `command` to be `deploy_iac_rules_get` to get the best practices rules for iac generation.
- **Authentication**: Proper managed identity and RBAC configuration
- **Monitoring**: Application Insights receiving telemetry

## Failure Recovery & Troubleshooting

### Common Issues & Solutions
1. **Policy Violations**: Switch to Azure CLI deployment methods
2. **Missing Dependencies**: Systematic tool installation and validation
3. **Authentication Issues**: Comprehensive RBAC and managed identity setup
4. **Runtime Compatibility**: Use supported versions (Node.js 20+, Python 3.11+)
5. **Partial Deployments**: Clean resource group deletion before retry

### Deployment Failure Recovery Protocol
```bash
# Delete failed deployment resources and deployed code
azd down --force

# Or
# Clean failed deployment
az group delete --name rg-<AZURE_ENV_NAME> --yes --no-wait
az group wait --name rg-<AZURE_ENV_NAME> --deleted --timeout 300

# Retry deployment
azd up
```

## Reference Resources

### Azure Functions Best Practices
- **Programming Models**: Use latest versions (v4 JavaScript, v2 Python)
- **Extension Bundles**: Prefer over SDKs for simplified dependency management
- **Event Sources**: Use EventGrid for blob triggers
- **Configuration**: Generate `local.settings.json` for local development

### Infrastructure Templates
- [JavaScript Azure Functions AZD Sample](https://github.com/Azure-Samples/functions-quickstart-javascript-azd/tree/main/infra)
- [.NET Azure Functions with EventGrid Sample](https://github.com/Azure-Samples/functions-quickstart-dotnet-azd-eventgrid-blob/tree/main/infra)