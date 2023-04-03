using Azure.Storage.Blobs;
using IMJohn.Services;
using Microsoft.AspNetCore.Mvc;
using Microsoft.SemanticKernel.Orchestration;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace IMJohn.Controllers
{
    [ApiController]
    [Route("/")]
    public class ApiController : Controller
    {
        private readonly BlobServiceClient blobServiceClient;
        private readonly BlobContainerClient blobContainerClient;
        private readonly RetrieveThenReadApproachService retrieveThenReadApproachService;

        public ApiController(BlobServiceClient blobServiceClient, BlobContainerClient blobContainerClient, RetrieveThenReadApproachService retrieveThenReadApproachService)
        {
            this.blobServiceClient = blobServiceClient;
            this.blobContainerClient = blobContainerClient;
            this.retrieveThenReadApproachService = retrieveThenReadApproachService;
        }

        [HttpGet]
        [Route("content/{citation}")]
        public async Task<IActionResult> GetContentAsync(string citation)
        {
            // find out if citation exists in this.blobContainerClient
            // if it does, return the content
            // if it doesn't, return 404
            if(!await this.blobContainerClient.ExistsAsync())
                return this.NotFound("blob container not found");

            var fileContent = await this.blobContainerClient.GetBlobClient(citation).DownloadContentAsync();

            if (fileContent == null)
            {
                return this.NotFound($"{citation} not found");
            }
            else
            {
                return this.Ok(fileContent);
            }
        }

        [HttpPost]
        [Route("chat")]
        [Produces("application/json")]
        public Task<IActionResult> PostChatAsync()
        {
            throw new NotImplementedException();
        }

        [HttpPost]
        [Route("ask")]
        [Produces("application/json")]
        public async Task<IActionResult> PostAskAsync()
        {
            // get question from body
            var json = await new StreamReader(this.Request.Body).ReadToEndAsync();
            var doc = JsonNode.Parse(json);
            if (doc!["question"]?.GetValue<string>() is string question)
            {
                var variable = new ContextVariables();
                variable["question"] = question;
                var res = await this.retrieveThenReadApproachService.RunAsync(variable, null);

                return this.Ok(res);
            }

            return this.BadRequest();
        }
    }
}
