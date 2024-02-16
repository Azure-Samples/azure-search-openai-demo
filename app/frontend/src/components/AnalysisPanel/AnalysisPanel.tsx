import { Stack, Pivot, PivotItem } from "@fluentui/react";
import SyntaxHighlighter from "react-syntax-highlighter";
import { useMutation } from "react-query";

import styles from "./AnalysisPanel.module.css";

import { SupportingContent } from "../SupportingContent";
import { ChatAppResponse } from "../../api";
import { AnalysisPanelTabs } from "./AnalysisPanelTabs";
import { ThoughtProcess } from "./ThoughtProcess";
import { useMsal } from "@azure/msal-react";
import { getHeaders } from "../../api";
import { useLogin, getToken } from "../../authConfig";
import { useState, useEffect } from "react";
import { Evaluation } from "./Evaluation";

interface Props {
    className: string;
    activeTab: AnalysisPanelTabs;
    onActiveTabChanged: (tab: AnalysisPanelTabs) => void;
    activeCitation: string | undefined;
    citationHeight: string;
    answer: ChatAppResponse;
    question: string;
}

const pivotItemDisabledStyle = { disabled: true, style: { color: "grey" } };

export const AnalysisPanel = ({ answer, activeTab, activeCitation, citationHeight, className, onActiveTabChanged, question }: Props) => {
    const isDisabledThoughtProcessTab: boolean = !answer.choices[0].context.thoughts;
    const isDisabledSupportingContentTab: boolean = !answer.choices[0].context.data_points;
    const isDisabledCitationTab: boolean = !activeCitation;
    const [citation, setCitation] = useState("");

    const client = useLogin ? useMsal().instance : undefined;

    const fetchCitation = async () => {
        const token = client ? await getToken(client) : undefined;

        if (activeCitation) {
            const page = activeCitation.split("#")[1];
            // Get the end of the string starting from "#"
            const response = await fetch(activeCitation, {
                method: "GET",
                headers: getHeaders(token)
            });
            const citationContent = await response.blob();
            var citationObjectUrl;
            if (page !== "page=1") {
                citationObjectUrl = URL.createObjectURL(citationContent) + "#" + page;
            } else {
                citationObjectUrl = URL.createObjectURL(citationContent) + "#" + "page=2";
            }
            setCitation(citationObjectUrl);
        }
    };
    useEffect(() => {
        fetchCitation();
    }, []);

    return (
        <Pivot
            className={className}
            selectedKey={activeTab}
            onLinkClick={pivotItem => pivotItem && onActiveTabChanged(pivotItem.props.itemKey! as AnalysisPanelTabs)}
        >
            <PivotItem
                itemKey={AnalysisPanelTabs.ThoughtProcessTab}
                headerText="Thought process"
                headerButtonProps={isDisabledThoughtProcessTab ? pivotItemDisabledStyle : undefined}
            >
                <ThoughtProcess thoughts={answer.choices[0].context.thoughts || []} />
            </PivotItem>
            <PivotItem
                itemKey={AnalysisPanelTabs.SupportingContentTab}
                headerText="Supporting content"
                headerButtonProps={isDisabledSupportingContentTab ? pivotItemDisabledStyle : undefined}
            >
                <SupportingContent supportingContent={answer.choices[0].context.data_points} />
            </PivotItem>
            <PivotItem
                itemKey={AnalysisPanelTabs.EvaluationTab}
                headerText="Evaluation"
                headerButtonProps={isDisabledSupportingContentTab ? pivotItemDisabledStyle : undefined}
            >
                <Evaluation question={question} answer={answer.choices[0].message.content} supportingContent={answer.choices[0].context.data_points} />
            </PivotItem>
            <PivotItem
                itemKey={AnalysisPanelTabs.CitationTab}
                headerText="Citation"
                headerButtonProps={isDisabledCitationTab ? pivotItemDisabledStyle : undefined}
            >
                {activeCitation?.endsWith(".png") ? (
                    <img src={citation} className={styles.citationImg} />
                ) : (
                    <iframe title="Citation" src={citation} width="100%" height={citationHeight} />
                )}
            </PivotItem>
        </Pivot>
    );
};
