import { useMsal } from "@azure/msal-react";
import { Tab, TabList, SelectTabData, SelectTabEvent } from "@fluentui/react-components";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { ChatAppResponse, getHeaders } from "../../api";
import { getToken, useLogin } from "../../authConfig";
import { MarkdownViewer } from "../MarkdownViewer";
import { SupportingContent } from "../SupportingContent";
import styles from "./AnalysisPanel.module.css";
import { AnalysisPanelTabs } from "./AnalysisPanelTabs";
import { ThoughtProcess } from "./ThoughtProcess";

interface Props {
    className: string;
    activeTab: AnalysisPanelTabs;
    onActiveTabChanged: (tab: AnalysisPanelTabs) => void;
    activeCitation: string | undefined;
    citationHeight: string;
    answer: ChatAppResponse;
    onCitationClicked?: (citationFilePath: string) => void;
}

export const AnalysisPanel = ({ answer, activeTab, activeCitation, citationHeight, className, onActiveTabChanged, onCitationClicked }: Props) => {
    const isDisabledThoughtProcessTab: boolean = !answer.context.thoughts;
    const dataPoints = answer.context.data_points;
    const hasSupportingContent = Boolean(
        dataPoints &&
            ((dataPoints.text && dataPoints.text.length > 0) ||
                (dataPoints.images && dataPoints.images.length > 0) ||
                (dataPoints.external_results_metadata && dataPoints.external_results_metadata.length > 0))
    );
    const isDisabledSupportingContentTab: boolean = !hasSupportingContent;
    const isDisabledCitationTab: boolean = !activeCitation;
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
        <div className={className}>
            <TabList selectedValue={activeTab} onTabSelect={(_ev: SelectTabEvent, data: SelectTabData) => onActiveTabChanged(data.value as AnalysisPanelTabs)}>
                <Tab value={AnalysisPanelTabs.ThoughtProcessTab} disabled={isDisabledThoughtProcessTab}>
                    {t("headerTexts.thoughtProcess")}
                </Tab>
                <Tab value={AnalysisPanelTabs.SupportingContentTab} disabled={isDisabledSupportingContentTab}>
                    {t("headerTexts.supportingContent")}
                </Tab>
                <Tab value={AnalysisPanelTabs.CitationTab} disabled={isDisabledCitationTab}>
                    {t("headerTexts.citation")}
                </Tab>
            </TabList>
            <div>
                {activeTab === AnalysisPanelTabs.ThoughtProcessTab && (
                    <ThoughtProcess thoughts={answer.context.thoughts || []} onCitationClicked={onCitationClicked} />
                )}
                {activeTab === AnalysisPanelTabs.SupportingContentTab && <SupportingContent supportingContent={answer.context.data_points} />}
                {activeTab === AnalysisPanelTabs.CitationTab && renderFileViewer()}
            </div>
        </div>
    );
};
