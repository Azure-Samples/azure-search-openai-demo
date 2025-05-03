import React from "react";
import { TokenUsageGraph, TokenUsage } from "./TokenUsageGraph";
import { Light as SyntaxHighlighter } from "react-syntax-highlighter";
import { a11yLight } from "react-syntax-highlighter/dist/esm/styles/hljs";
import json from "react-syntax-highlighter/dist/esm/languages/hljs/json";
import styles from "./AnalysisPanel.module.css";
SyntaxHighlighter.registerLanguage("json", json);

type ModelQueryPlanningStep = {
  id: number;
  type: "ModelQueryPlanning";
  input_tokens: number;
  output_tokens: number;
};

type AzureSearchQueryStep = {
  id: number;
  type: "AzureSearchQuery";
  target_index: string;
  query: { search: string };
  query_time: string;
  count: number;
  elapsed_ms: number;
};

type Step = ModelQueryPlanningStep | AzureSearchQueryStep;

interface Props {
  description: Step[];
}

export const AgentPlan: React.FC<Props> = ({ description }) => {
  // find the planning step
  const planning = description.find(
    (step): step is ModelQueryPlanningStep => step.type === "ModelQueryPlanning"
  );

  // collect all search query steps
  const queries = description.filter(
    (step): step is AzureSearchQueryStep => step.type === "AzureSearchQuery"
  );

  return (
    <div>
      {planning && (
        <TokenUsageGraph
          title="Query Planning Token Usage"
          tokenUsage={
            {
              prompt_tokens: planning.input_tokens,
              completion_tokens: planning.output_tokens,
              reasoning_tokens: 0,
              total_tokens: planning.input_tokens + planning.output_tokens,
            } as TokenUsage
          }
        />
      )}

      {queries.map((q) => (
        <div key={q.id} style={{ marginTop: 8 }}>
            <SyntaxHighlighter language="json" wrapLongLines className={styles.tCodeBlock} style={a11yLight}>
                {JSON.stringify(q, null, 2)}
            </SyntaxHighlighter>
        </div>
      ))}
    </div>
  );
};