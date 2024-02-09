import { IconButton } from "@fluentui/react";

import { useState } from "react";
import EvalItemDetailed from "../EvalItem/EvalItemDetailed";
import EvalItem from "../EvalItem/EvalItem";
import BatchScorecard from "./BatchScorecard";

interface Props {
    jsonData: any;
    onRemove: () => void;
}

const BatchExperiment = ({ jsonData, onRemove }: Props) => {
    const [activeSample, setActiveSample] = useState<any>(null);

    console.log(jsonData);

    const params = jsonData["parameters.json"];
    const results = jsonData["eval_results.jsonl"];
    const summ = jsonData["summary.json"];

    const setActiveSampleQ = (question: string) => {
        const newActiveSample = results.find((sample: any) => sample.question === question);
        console.log(newActiveSample);
        setActiveSample(newActiveSample);
    };

    const removeActiveSample = () => {
        setActiveSample(null);
    };

    return (
        <div>
            <IconButton
                style={{ color: "black" }}
                iconProps={{ iconName: "ChevronLeftMed" }}
                title="Back to overview"
                ariaLabel="Back to overview"
                onClick={() => onRemove()}
            />
            <BatchScorecard experimentName="Test Experiment 1" summ={summ} />
            <section>
                {activeSample ? (
                    <EvalItemDetailed
                        question={activeSample.question}
                        answer={activeSample.answer}
                        context={activeSample.context}
                        relevance={activeSample.gpt_relevance}
                        coherence={activeSample.gpt_coherence}
                        similarity={activeSample.gpt_similarity}
                        groundedness={activeSample.gpt_groundedness}
                        removeActiveSample={removeActiveSample}
                    />
                ) : (
                    <>
                        {results.map((evalItem: any) => (
                            <EvalItem
                                key={evalItem.id}
                                id={evalItem.id}
                                question={evalItem.question}
                                answer={evalItem.answer}
                                relevance={evalItem.gpt_relevance}
                                coherence={evalItem.gpt_coherence}
                                similarity={evalItem.gpt_similarity}
                                groundedness={evalItem.gpt_groundedness}
                                setActiveSample={setActiveSampleQ}
                            />
                        ))}
                    </>
                )}
            </section>
        </div>
    );
};
export default BatchExperiment;
