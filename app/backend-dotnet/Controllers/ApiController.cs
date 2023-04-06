namespace Controllers;

using Azure.Storage.Blobs;
using Microsoft.AspNetCore.Mvc;
using Microsoft.SemanticKernel.Orchestration;
using Services;
using System.Text.Json.Nodes;

[ApiController]
[Route("/")]
public class ApiController : Controller
{
    private readonly BlobServiceClient _blobServiceClient;
    private readonly BlobContainerClient _blobContainerClient;
    private readonly RetrieveThenReadApproachService _retrieveThenReadApproachService;

    public ApiController(BlobServiceClient blobServiceClient, BlobContainerClient blobContainerClient, RetrieveThenReadApproachService retrieveThenReadApproachService)
    {
        _blobServiceClient = blobServiceClient;
        _blobContainerClient = blobContainerClient;
        _retrieveThenReadApproachService = retrieveThenReadApproachService;
    }

    [HttpGet]
    [Route("content/{citation}")]
    public async Task<IActionResult> GetContentAsync(string citation)
    {
        // find out if citation exists in this.blobContainerClient
        // if it does, return the content
        // if it doesn't, return 404
        if (!await _blobContainerClient.ExistsAsync())
            return NotFound("blob container not found");

        var fileContent = await _blobContainerClient.GetBlobClient(citation).DownloadContentAsync();

        if (fileContent == null)
        {
            return NotFound($"{citation} not found");
        }
        else
        {
            return Ok(fileContent);
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
        var json = await new StreamReader(Request.Body).ReadToEndAsync();
        var doc = JsonNode.Parse(json);
        if (doc!["question"]?.GetValue<string>() is string question)
        {
            var variable = new ContextVariables();
            variable["question"] = question;
            var res = await _retrieveThenReadApproachService.RunAsync(variable, null);

            return Ok(res);
        }

        return BadRequest();
    }
}
