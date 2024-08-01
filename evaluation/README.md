# Evaluation Process

This directory contains scripts and tools based on
[Azure-Samples/ai-rag-chat-evaluator](https://github.com/Azure-Samples/ai-rag-chat-evaluator)
and [Azure/PyRIT](https://github.com/Azure/PyRIT) to perform evaluation and red teaming on the chat app.
By default, the OpenAI GPT model is used as the evaluator to perform the evaluation.
As an alternative, you can either use an Azure-hosted OpenAI instance or openai.com.

## Prerequisites

All of the following instructions assume that you're running commands from inside the directory of the repository.
Before using the evaluation scripts, you'll need to:

- Have a live deployment of the chat application on Azure
- Be on an Azure-authenticated shell session.
  You can run the following command to ensure you're logged in before proceeding:

  ```shell
  az login
  ```

- Create a `.env` file with environment variables required by the evaluation scripts.
  You can follow the instructions in the [following](#create-env-file) section to achieve that.

### Create .env file

If you already have an existing deployment and an active `azd` environment, you can create the required .env file
by running the appropriate script depending on your platform:

```shell
# Shell
./scripts/create_eval_dotenv.sh

# Powershell
# If you encounter a permission error, you might need to change the execution policy to allow script execution.
# You can do this by running:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
.\scripts\create_eval_dotenv.ps1
```

### Change LLM used for evaluation

The provided solution offers multiple configuration combinations.
One of the most important ones is tweaking the LLM used for evaluation, with a few options currently exposed:

- OpenAI GPT on Azure (default)
- Other models deployed on Azure ML
- Instances provided by openai.com

In order to change the default behaviour, you will have to set the corresponding environment variables before running
the `create_eval_dotenv` script.

If you want to use other ML models deployed on Azure, you need to set the following environment varibles:

```shell
# Shell
export AZURE_ML_ENDPOINT="<deployment-endpoint>"
export AZURE_ML_MANAGED_KEY="<access-key>"

# Powershell
$env:AZURE_ML_ENDPOINT = "<deployment-endpoint>"
$env:AZURE_ML_MANAGED_KEY = "<access-key>"
```

On the other hand, to use instances deployed on openai.com, you need to set the following environment varibles:

```shell
# Shell
export OPENAICOM_ORGANIZATION="<openai-organization-name>"
export OPENAICOM_KEY="<access-key>"

# Powershell
$env:OPENAICOM_ORGANIZATION = "<openai-organization-name>"
$env:OPENAICOM_KEY = "<access-key>"
```

## Generate synthetic data for evaluation

In order to run the evaluator, you must first create a set of of questions with corresponding "ground truth" answers
which represent the ideal response to each question.
This is possible using the `generate` script which generates synthetic data based on documents stored in the deployed
Azure AI Search instance.
You can run it like this, specifying the path of the generated output file, the desired number of total question-answer
pairs, as well as the number of pairs per source (i.e. document):

```shell
python -m evaluation generate \
  --output=evaluation/input/qa.jsonl \
  --numquestions=200 \
  --persource=5
```

Running the above will generate 200 question-answer pairs and store them in `evaluation/input/qa.jsonl`.

### Generate answers for Azure AI Studio evaluation

After generating the questions, you can run the command below to instruct the LLM to gererate the answers in a format
that can be used as raw data to conduct evaluation through the Azure AI Studio:

```shell
python -m evaluation generate-answers \
  --input=evaluation/input/qa.jsonl \
  --output=evaluation/output/qa_answers.jsonl
```

## Run evaluation

You can run the evaluation script with the following command, specifying the path to the configuration file
(the provided [evaluation/config.json](./config.json) will be used by default; feel free to edit it or provide your
own), as well as the number of questions considered (by default, all questions found in the input file will be
consumed).

```shell
python -m evaluation evaluate \
  --config=evaluation/config.json \
  --numquestions=2
```

### Specify desired evaluation metrics

The evaluation script will use the metrics specified in the `requested_metrics` field of the config JSON.
Some of those metrics are built-in to the evaluation SDK, while others are custom.

#### Built-in metrics

These metrics are calculated by sending a call to the GPT model, asking it to provide a 1-5 rating, and storing that rating.

> [!IMPORTANT]
> The generator script can only generate English Q/A pairs right now, due to [limitations in the azure-ai-generative SDK](https://github.com/Azure/azure-sdk-for-python/issues/34099).

- [`gpt_coherence`](https://learn.microsoft.com/azure/ai-studio/concepts/evaluation-metrics-built-in#ai-assisted-coherence) measures how well the language model can produce output that flows smoothly, reads naturally, and resembles human-like language.
- [`gpt_relevance`](https://learn.microsoft.com/azure/ai-studio/concepts/evaluation-metrics-built-in#ai-assisted-relevance) assesses the ability of answers to capture the key points of the context.
- [`gpt_groundedness`](https://learn.microsoft.com/azure/ai-studio/concepts/evaluation-metrics-built-in#ai-assisted-groundedness) assesses the correspondence between claims in an AI-generated answer and the source context, making sure that these claims are substantiated by the context.
- [`gpt_similarity`](https://learn.microsoft.com/azure/ai-studio/concepts/evaluation-metrics-built-in#ai-assisted-gpt-similarity) measures the similarity between a source data (ground truth) sentence and the generated response by an AI model.
- [`gpt_fluency`](https://learn.microsoft.com/azure/ai-studio/concepts/evaluation-metrics-built-in#ai-assisted-fluency) measures the grammatical proficiency of a generative AI's predicted answer.
- [`f1_score`](https://learn.microsoft.com/azure/ai-studio/concepts/evaluation-metrics-built-in#traditional-machine-learning-f1-score) Measures the ratio of the number of shared words between the model generation and the ground truth answers.

### GPT evaluation results

The results of each evaluation are stored in the specified results directory, in a timestamped
`gpt_evaluation/experiment-XXXXXXXXXX` subdirectory that contains:

- `config.json`: The original config used for the run. This is useful for reproducing the run.
- `eval_results.jsonl`: Each question and answer, along with the GPT metrics for each QA pair.
- `eval.png`: The chart for the evaluation results corresponding to answer length and latency.
- `mean_score.png`: The chart for the mean score of evaluation metrics.
- `passing_rate.png`: The chart for the passing rate of evaluation metrics.
- `summary.json`: The overall results, e.g. average GPT metrics.

## Run red teaming evaluation

When running the red teaming script, you can opt to execute it against the entire chat application (recommended) or
just the model used as part of it.

### Run the red teaming script against the entire application

The default and recommended target of the red teaming attack is the entire application (specified explicitly below):

```shell
python -m evaluation red-teaming \
  --prompt-target="application" \
  --scorer-dir=evaluation/scorer_definitions \
  --config=evaluation/config.json
```

`scorer-dir` is a directory that contains the customised scorer YAML files (set to the `evaluation/scorer_definitions` directory by default). Each scorer is defined by a YAML file that needs to contain the following fields:

- `category`
- `true_description`
- `false_description`

### Run the red teaming script against the target OpenAI model on Azure

You can set the `--prompt-target` to `"azureopenai"` to target an Azure-hosted OpenAI model:

```shell
python -m evaluation red-teaming \
  --prompt-target="azureopenai" \
  --scorer-dir=evaluation/scorer_definitions \
  --config=evaluation/config.json
```

### Run the red teaming script against other ML models on Azure

You can set the `--prompt-target` to `"azureml"` to target a different Azure-hosted model:

```shell
python -m evaluation red-teaming \
  --prompt-target="azureml" \
  --scorer-dir=evaluation/scorer_definitions \
  --config=evaluation/config.json
```

### View red teaming evaluation results

The results of each red teaming experiment are stored in the specified results directory, in a timestamped
`red_teaming/experiment-XXXXXXXXXX` subdirectory that contains a `scores.json` file with the result.
