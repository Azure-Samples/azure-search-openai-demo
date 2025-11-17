import { Stack, Pivot, PivotItem } from "@fluentui/react";
import { useTranslation } from "react-i18next";
import styles from "./AnalysisPanel.module.css";

import { SupportingContent } from "../SupportingContent";
import { ChatAppResponse } from "../../api";
import { AnalysisPanelTabs } from "./AnalysisPanelTabs";
import { ThoughtProcess } from "./ThoughtProcess";
import { MarkdownViewer } from "../MarkdownViewer";
import { useMsal } from "@azure/msal-react";
import { getHeaders } from "../../api";
import { useLogin, getToken } from "../../authConfig";
import { useState, useEffect, useMemo } from "react";
import { extractCitationDetails } from "../Answer/AnswerParser";

interface Props {
    className: string;
    activeTab: AnalysisPanelTabs;
    onActiveTabChanged: (tab: AnalysisPanelTabs) => void;
    activeCitation: string | undefined;
    citationHeight: string;
    answer: ChatAppResponse;
}

const pivotItemDisabledStyle = { disabled: true, style: { color: "grey" } };

export const AnalysisPanel = ({ answer, activeTab, activeCitation, citationHeight, className, onActiveTabChanged }: Props) => {
    const isDisabledThoughtProcessTab: boolean = !answer.context.thoughts;
    const dataPoints = answer.context.data_points;
    const hasSupportingContent = Boolean(
        dataPoints &&
            ((dataPoints.text && dataPoints.text.length > 0) ||
                (dataPoints.images && dataPoints.images.length > 0) ||
                (dataPoints.web && dataPoints.web.length > 0))
    );
    const isDisabledSupportingContentTab: boolean = !hasSupportingContent;
    const isDisabledCitationTab: boolean = !activeCitation;
    const citationDetails = useMemo(() => extractCitationDetails(answer), [answer]);
    const [citation, setCitation] = useState("");

    const client = useLogin ? useMsal().instance : undefined;
    const { t } = useTranslation();

    const fetchCitation = async () => {
        const token = client ? await getToken(client) : undefined;
        if (activeCitation) {
            // Get hash from the URL as it may contain #page=N
            // which helps browser PDF renderer jump to correct page N
            const originalHash = activeCitation.indexOf("#") ? activeCitation.split("#")[1] : "";
            const response = await fetch(activeCitation, {
                method: "GET",
                headers: await getHeaders(token)
            });
            const citationContent = await response.blob();
            let citationObjectUrl = URL.createObjectURL(citationContent);
            // Add hash back to the new blob URL
            if (originalHash) {
                citationObjectUrl += "#" + originalHash;
            }
            setCitation(citationObjectUrl);
        }
    };
    useEffect(() => {
        fetchCitation();
    }, []);

    const renderFileViewer = () => {
        if (!activeCitation) {
            return null;
        }

        const fileExtension = activeCitation.split(".").pop()?.toLowerCase();
        switch (fileExtension) {
            case "png":
                return <img src={citation} className={styles.citationImg} alt="Citation Image" />;
            case "md":
                return <MarkdownViewer src={activeCitation} />;
            default:
                return <iframe title="Citation" src={citation} width="100%" height={citationHeight} />;
        }
    };

    return (
        <Pivot
            className={className}
            selectedKey={activeTab}
            onLinkClick={pivotItem => pivotItem && onActiveTabChanged(pivotItem.props.itemKey! as AnalysisPanelTabs)}
        >
            <PivotItem
                itemKey={AnalysisPanelTabs.ThoughtProcessTab}
                headerText={t("headerTexts.thoughtProcess")}
                headerButtonProps={isDisabledThoughtProcessTab ? pivotItemDisabledStyle : undefined}
            >
                <ThoughtProcess thoughts={answer.context.thoughts || []} citationDetails={citationDetails} webDataPoints={answer.context.data_points.web} />
            </PivotItem>
            <PivotItem
                itemKey={AnalysisPanelTabs.SupportingContentTab}
                headerText={t("headerTexts.supportingContent")}
                headerButtonProps={isDisabledSupportingContentTab ? pivotItemDisabledStyle : undefined}
            >
                <SupportingContent supportingContent={answer.context.data_points} />
            </PivotItem>
            <PivotItem
                itemKey={AnalysisPanelTabs.CitationTab}
                headerText={t("headerTexts.citation")}
                headerButtonProps={isDisabledCitationTab ? pivotItemDisabledStyle : undefined}
            >
                {renderFileViewer()}
            </PivotItem>
        </Pivot>
    );
};
