namespace Services;

using Azure.AI.OpenAI;
using Microsoft.SemanticKernel.AI;
using Microsoft.SemanticKernel.AI.TextCompletion;

internal sealed class AzureOpenAITextCompletionService : ITextCompletion
{
    private readonly OpenAIClient _openAIClient;
    private readonly string _deployedModelName;

    public AzureOpenAITextCompletionService(OpenAIClient openAIClient, string deployedModelName)
    {
        _openAIClient = openAIClient;
        _deployedModelName = deployedModelName;
    }

    public async Task<string> CompleteAsync(string text, CompleteRequestSettings requestSettings, CancellationToken cancellationToken = default)
    {
        var option = new CompletionsOptions();
        option.Prompts.Add(text);
        option.Temperature = Convert.ToSingle(requestSettings.Temperature);
        foreach (var stopSequence in requestSettings.StopSequences)
        {
            option.StopSequences.Add(stopSequence);
        }

        option.MaxTokens = requestSettings.MaxTokens;
        option.FrequencyPenalty = Convert.ToSingle(requestSettings.FrequencyPenalty);
        option.PresencePenalty = Convert.ToSingle(requestSettings.PresencePenalty);

        var response = await _openAIClient.GetCompletionsAsync(_deployedModelName, option, cancellationToken);
        if (response.Value is Completions completions && completions.Choices.Count >= 1)
        {
            return completions.Choices.First().Text;
        }
        else
        {
            throw new AIException(AIException.ErrorCodes.InvalidConfiguration, "completion not found");
        }
    }
}
