using Azure.AI.OpenAI;
using Azure.Identity;
using Azure.Search.Documents;
using Azure.Storage.Blobs;
using Microsoft.SemanticKernel;
using Services;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
// See: https://aka.ms/aspnetcore/swashbuckle
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen();

var azureCredential = new DefaultAzureCredential();
var AZURE_STORAGE_ACCOUNT = builder.Configuration["AZURE_STORAGE_ACCOUNT"];

// Add blob service client
var blobServiceClient = new BlobServiceClient(new Uri($"https://{AZURE_STORAGE_ACCOUNT}.blob.core.windows.net"), azureCredential);
builder.Services.AddSingleton(blobServiceClient);

// Add blob container client
var AZURE_STORAGE_CONTAINER = builder.Configuration["AZURE_STORAGE_CONTAINER"];
var blobContainerClient = blobServiceClient.GetBlobContainerClient(AZURE_STORAGE_CONTAINER);
builder.Services.AddSingleton(blobContainerClient);

// Add search client
var AZURE_SEARCH_SERVICE = builder.Configuration["AZURE_SEARCH_SERVICE"];
var AZURE_SEARCH_INDEX = builder.Configuration["AZURE_SEARCH_INDEX"];
var searchClient = new SearchClient(new Uri($"https://{AZURE_SEARCH_SERVICE}.search.windows.net"), AZURE_SEARCH_INDEX, azureCredential);
builder.Services.AddSingleton(searchClient);

// add semantic kernel
var AZURE_OPENAI_CHATGPT_DEPLOYMENT = builder.Configuration["AZURE_OPENAI_CHATGPT_DEPLOYMENT"];
var AZURE_OPENAI_GPT_DEPLOYMENT = builder.Configuration["AZURE_OPENAI_GPT_DEPLOYMENT"];
var AZURE_OPENAI_SERVICE = builder.Configuration["AZURE_OPENAI_SERVICE"];
var openAIClient = new OpenAIClient(new Uri($"https://{AZURE_OPENAI_SERVICE}.openai.azure.com"), azureCredential);

// semantic kernel doesn't support Azure AAD credential for now
// so we implement our own textcompletion backend
var openAIService = new AzureOpenAITextCompletionService(openAIClient, AZURE_OPENAI_GPT_DEPLOYMENT);
var kernel = Kernel.Builder.Build();
kernel.Config.AddTextCompletion(AZURE_OPENAI_GPT_DEPLOYMENT, (kernel) => openAIService, true);
builder.Services.AddSingleton(kernel);

// add RetrieveThenReadApproachService
builder.Services.AddSingleton(new RetrieveThenReadApproachService(searchClient, kernel));
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
