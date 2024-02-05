import { useState } from "react";
import EvalItem from "../../components/EvalItem/EvalItem";

import * as fb from "../../../../backend/feedback.json";
import EvalSidebar from "../../components/EvalSidebar/EvalSidebar";
import EvalItemDetailed from "../../components/EvalItem/EvalItemDetailed";

import styles from "./Eval.module.css";

const str: string = JSON.stringify(fb);
const evalItems: { default: any[] } = JSON.parse(str);

export function Component(): JSX.Element {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [data, setData] = useState<any>({ evalItems });
    const [activeSample, setActiveSample] = useState<any>(null);

    const setActiveSampleId = (id: number) => {
        const newActiveSample = data.evalItems.default.find((sample: any) => sample.id === id);
        setActiveSample(newActiveSample);
        console.log(newActiveSample);
    };

    const removeActiveSample = () => {
        setActiveSample(null);
    };

    return (
        <div className={styles.layout}>
            <EvalSidebar />
            <section className={styles.mainContent}>
                {isLoading ? (
                    <p>Loading...</p>
                ) : activeSample ? (
                    <EvalItemDetailed
                        id={activeSample.id}
                        feedback={activeSample.feedback}
                        question={activeSample.question}
                        answer={activeSample.answer}
                        removeActiveSample={removeActiveSample}
                    />
                ) : (
                    <>
                        {data.evalItems.default.map((evalItem: any) => (
                            <EvalItem
                                key={evalItem.id}
                                id={evalItem.id}
                                feedback={evalItem.feedback}
                                question={evalItem.question}
                                answer={evalItem.answer}
                                setActiveSample={setActiveSampleId}
                            />
                        ))}
                    </>
                )}
            </section>
        </div>
    );
}
