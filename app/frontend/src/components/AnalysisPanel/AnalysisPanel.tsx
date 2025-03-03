import { Stack, Pivot, PivotItem, Modal, IconButton } from "@fluentui/react";
import { useState, useEffect } from "react";
import { useMsal } from "@azure/msal-react";

import styles from "./AnalysisPanel.module.css";
import { SupportingContent } from "../SupportingContent";
import { ChatAppResponse } from "../../api";
import { AnalysisPanelTabs } from "./AnalysisPanelTabs";
import { ThoughtProcess } from "./ThoughtProcess";
import { MarkdownViewer } from "../MarkdownViewer";
import { getHeaders } from "../../api";
import { useLogin, getToken } from "../../authConfig";

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
    const isDisabledSupportingContentTab: boolean = !answer.context.data_points;
    const isDisabledCitationTab: boolean = !activeCitation;
    const [citation, setCitation] = useState("");
    const [isModalOpen, setIsModalOpen] = useState(false);

    const client = useLogin ? useMsal().instance : undefined;


    const fetchCitation = async () => {
        const token = client ? await getToken(client) : undefined;
        if (activeCitation) {
            const originalHash = activeCitation.indexOf("#") ? activeCitation.split("#")[1] : "";
            const response = await fetch(activeCitation, {
                method: "GET",
                headers: getHeaders(token)
            });
            const citationContent = await response.blob();
            let citationObjectUrl = URL.createObjectURL(citationContent);
            if (originalHash) {
                citationObjectUrl += "#" + originalHash;
            }
            setCitation(citationObjectUrl);
            setIsModalOpen(true);
        }
    };

    useEffect(() => {
        fetchCitation();
    }, [activeCitation]);

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
        <>
            <Pivot
                className={className}
                selectedKey={activeTab}
                onLinkClick={pivotItem => pivotItem && onActiveTabChanged(pivotItem.props.itemKey! as AnalysisPanelTabs)}
            >
                {/* <PivotItem
                    itemKey={AnalysisPanelTabs.ThoughtProcessTab}
                    headerText="Thought process"
                    headerButtonProps={isDisabledThoughtProcessTab ? pivotItemDisabledStyle : undefined}
                >
                    <ThoughtProcess thoughts={answer.context.thoughts || []} />
                </PivotItem> */}
                <PivotItem
                    itemKey={AnalysisPanelTabs.SupportingContentTab}
                    headerText="Supporting content"
                    headerButtonProps={isDisabledSupportingContentTab ? pivotItemDisabledStyle : undefined}
                >
                    <SupportingContent supportingContent={answer.context.data_points} />
                </PivotItem>
               {/* <PivotItem
                    itemKey={AnalysisPanelTabs.CitationTab}
                    headerText="Citation"
                    headerButtonProps={isDisabledCitationTab ? pivotItemDisabledStyle : undefined}
                >
                </PivotItem>*/}
            </Pivot>
            {/* <Modal isOpen={isModalOpen} onDismiss={() => setIsModalOpen(false)} isBlocking={false} containerClassName={styles.modalContainer}>
                <div className={styles.modalHeader}>
                    <IconButton iconProps={{ iconName: "Cancel" }} ariaLabel="Close popup modal" onClick={() => setIsModalOpen(false)} />
                </div>
                <div className={styles.modalBody}>{renderFileViewer()}</div>
            </Modal> */}
<Modal
    isOpen={isModalOpen}
    onDismiss={() => setIsModalOpen(false)}
    isBlocking={false}
    containerClassName={styles.customModal}
    scrollableContentClassName={styles.noScrollModal} // Removes internal scroll
>
    <div className={styles.modalHeader}>
        <IconButton iconProps={{ iconName: "Cancel" }} ariaLabel="Close popup modal" onClick={() => setIsModalOpen(false)} />
    </div>
    <div className={styles.modalBody}>
        <div className={styles.pdfViewerContainer}>
            {renderFileViewer()}
        </div>
    </div>
</Modal>


        </>
    );
};
