using Azure;
using Azure.AI.OpenAI;
using Azure.Core;
using Azure.Identity;
using Azure.Search.Documents;
using Azure.Storage.Blobs;
using IMJohn.Services;
using Microsoft.Extensions.FileProviders;
using Microsoft.SemanticKernel;
using Microsoft.SemanticKernel.Configuration;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();
// Learn more about configuring Swagger/OpenAPI at https://aka.ms/aspnetcore/swashbuckle
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var azureCredential = new DefaultAzureCredential();
var AZURE_STORAGE_ACCOUNT = builder.Configuration.GetValue<string>("AZURE_STORAGE_ACCOUNT");

// Add blob service client
var blobServiceClient = new BlobServiceClient(new Uri($"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net"), azureCredential);
builder.Services.Add(ServiceDescriptor.Singleton(blobServiceClient));

// Add blob container client
var AZURE_STORAGE_CONTAINER = builder.Configuration.GetValue<string>("AZURE_STORAGE_CONTAINER");
var blobContainerClient = blobServiceClient.GetBlobContainerClient(AZURE_STORAGE_CONTAINER);
builder.Services.Add(ServiceDescriptor.Singleton(blobContainerClient));

// Add search client
var AZURE_SEARCH_SERVICE = builder.Configuration.GetValue<string>("AZURE_SEARCH_SERVICE");
var AZURE_SEARCH_INDEX = builder.Configuration.GetValue<string>("AZURE_SEARCH_INDEX");
var searchClient = new SearchClient(new Uri($"https://{AZURE_SEARCH_SERVICE}.search.windows.net"), AZURE_SEARCH_INDEX, azureCredential);
builder.Services.Add(ServiceDescriptor.Singleton(searchClient));

// add semantic kernel
var AZURE_OPENAI_CHATGPT_DEPLOYMENT = builder.Configuration.GetValue<string>("AZURE_OPENAI_CHATGPT_DEPLOYMENT");
var AZURE_OPENAI_GPT_DEPLOYMENT = builder.Configuration.GetValue<string>("AZURE_OPENAI_GPT_DEPLOYMENT");
var AZURE_OPENAI_SERVICE = builder.Configuration.GetValue<string>("AZURE_OPENAI_SERVICE");
var tokenRequestContext = new TokenRequestContext(new[] { "https://cognitiveservices.azure.com/.default" });
var openAIToken = azureCredential.GetToken(tokenRequestContext);
var openAIClient = new OpenAIClient(new Uri($"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"), azureCredential);
var openAIService = new AzureOpenAITextCompletionService(openAIClient, AZURE_OPENAI_GPT_DEPLOYMENT);
var kernel = Kernel.Builder.Build();
kernel.Config.AddTextCompletion(AZURE_OPENAI_GPT_DEPLOYMENT, (kernel) => openAIService, true);
builder.Services.Add(ServiceDescriptor.Singleton(kernel));

// add RetrieveThenReadApproachService
builder.Services.Add(ServiceDescriptor.Scoped<RetrieveThenReadApproachService, RetrieveThenReadApproachService>());
var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.UseDefaultFiles();
app.UseStaticFiles();

app.Run();
