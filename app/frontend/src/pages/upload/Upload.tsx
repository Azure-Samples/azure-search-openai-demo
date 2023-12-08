import { useRef, useState } from "react";

import styles from "./Upload.module.css";

import { askApi, ChatAppResponse, ChatAppRequest, RetrievalMode, uploadFilesApi, UploadFilesRequest } from "../../api";

import { AnalysisPanelTabs } from "../../components/AnalysisPanel";

import { useLogin, getToken } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { FileUploader } from "react-drag-drop-files";
import $ from "jquery";

const fileTypes = ["PDF"];
export function Component(): JSX.Element {
    // const [files, setFiles] = useState<any>(null);
    const [promptTemplate, setPromptTemplate] = useState<string>("");
    const [promptTemplatePrefix, setPromptTemplatePrefix] = useState<string>("");
    const [promptTemplateSuffix, setPromptTemplateSuffix] = useState<string>("");
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    const [retrieveCount, setRetrieveCount] = useState<number>(3);
    const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(true);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);
    const [excludeCategory, setExcludeCategory] = useState<string>("");
    const [useOidSecurityFilter, setUseOidSecurityFilter] = useState<boolean>(false);
    const [useGroupsSecurityFilter, setUseGroupsSecurityFilter] = useState<boolean>(false);

    const lastQuestionRef = useRef<string>("");

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();
    const [answer, setAnswer] = useState<ChatAppResponse>();

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    const client = useLogin ? useMsal().instance : undefined;

    const makeApiRequest = async (files: any) => {
        error && setError(undefined);
        setIsLoading(true);

        $.ajax({
            url: `/upload`,
            type: "POST",
            data: files,
            processData: false,
            contentType: false,
            success: function (data) {
                console.log("success");
                console.log(data);
                setIsLoading(false);
            },
            error: function (e){
                console.log("error");
                console.log(e);
                setIsLoading(false);
                setError(e);
            }
        });
    };

    const onPromptTemplateChange = (_ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setPromptTemplate(newValue || "");
    };

    const onPromptTemplatePrefixChange = (_ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setPromptTemplatePrefix(newValue || "");
    };

    const onPromptTemplateSuffixChange = (_ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setPromptTemplateSuffix(newValue || "");
    };

    const onRetrieveCountChange = (_ev?: React.SyntheticEvent<HTMLElement, Event>, newValue?: string) => {
        setRetrieveCount(parseInt(newValue || "3"));
    };

    const onUseSemanticRankerChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSemanticRanker(!!checked);
    };

    const onUseSemanticCaptionsChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSemanticCaptions(!!checked);
    };

    const onExcludeCategoryChanged = (_ev?: React.FormEvent, newValue?: string) => {
        setExcludeCategory(newValue || "");
    };

    const onShowCitation = (citation: string) => {
        if (activeCitation === citation && activeAnalysisPanelTab === AnalysisPanelTabs.CitationTab) {
            setActiveAnalysisPanelTab(undefined);
        } else {
            setActiveCitation(citation);
            setActiveAnalysisPanelTab(AnalysisPanelTabs.CitationTab);
        }
    };

    const onToggleTab = (tab: AnalysisPanelTabs) => {
        if (activeAnalysisPanelTab === tab) {
            setActiveAnalysisPanelTab(undefined);
        } else {
            setActiveAnalysisPanelTab(tab);
        }
    };

    const onUseOidSecurityFilterChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseOidSecurityFilter(!!checked);
    };

    const onUseGroupsSecurityFilterChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseGroupsSecurityFilter(!!checked);
    };

    const handleFilesSubmit = (e: any) => {
        e.preventDefault();
        const formData = new FormData(e.target);
        makeApiRequest(formData);
    };

    return (
        <div className={styles.uploadContainer}>
            <form method="POST" encType="multipart/form-data" onSubmit={handleFilesSubmit}>
                <FileUploader classes="file-uploader" name="file" types={fileTypes} multiple />
                <button type="submit">Submit</button>
                <progress id="progressBar" max="100" value="0"></progress>
            </form>
        </div>
    );
}

Component.displayName = "Upload";
