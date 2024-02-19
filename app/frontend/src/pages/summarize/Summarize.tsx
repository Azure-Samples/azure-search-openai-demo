import { useState, useEffect, useRef } from "react";

import styles from "./Summarize.module.css";

import SummarizeSelect from "../../components/Summarize/SummarizeSelect";
import SummarizeDocument from "../../components/Summarize/SummarizeDocument";

import { useMsal } from "@azure/msal-react";
import { getHeaders, RetrievalMode, GPT4VInput, VectorFieldOptions, ChatAppResponse, configApi, ChatAppRequest, askApi } from "../../api";
import { useLogin, getToken } from "../../authConfig";
import { GPT4VSettings } from "../../components/GPT4VSettings";
import { SettingsButton } from "../../components/SettingsButton/SettingsButton";
import { QuestionInput } from "../../components/QuestionInput";
import { IDropdownOption, Spinner } from "@fluentui/react";
import { Answer, AnswerError } from "../../components/Answer";
import SummarizeAnswer from "../../components/Answer/SummarizeAnswer";
import { ClearChatButton } from "../../components/ClearChatButton";

export function Component(): JSX.Element {
    const [document, setDocument] = useState<string>("");
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
    const [promptTemplate, setPromptTemplate] = useState<string>("");
    const [promptTemplatePrefix, setPromptTemplatePrefix] = useState<string>("");
    const [promptTemplateSuffix, setPromptTemplateSuffix] = useState<string>("");
    const [temperature, setTemperature] = useState<number>(0.3);
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    const [retrieveCount, setRetrieveCount] = useState<number>(3);
    const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(true);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);
    const [useGPT4V, setUseGPT4V] = useState<boolean>(false);
    const [gpt4vInput, setGPT4VInput] = useState<GPT4VInput>(GPT4VInput.TextAndImages);
    const [excludeCategory, setExcludeCategory] = useState<string>("");
    const [question, setQuestion] = useState<string>("");
    const [vectorFieldList, setVectorFieldList] = useState<VectorFieldOptions[]>([VectorFieldOptions.Embedding, VectorFieldOptions.ImageEmbedding]);
    const [useOidSecurityFilter, setUseOidSecurityFilter] = useState<boolean>(false);
    const [useGroupsSecurityFilter, setUseGroupsSecurityFilter] = useState<boolean>(false);
    const [showGPT4VOptions, setShowGPT4VOptions] = useState<boolean>(false);
    const [showSemanticRankerOption, setShowSemanticRankerOption] = useState<boolean>(false);
    const [showVectorOption, setShowVectorOption] = useState<boolean>(false);

    const lastQuestionRef = useRef<string>("");

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();
    const [answer, setAnswer] = useState<ChatAppResponse>();

    const client = useLogin ? useMsal().instance : undefined;

    const onDocumentClicked = (document: string) => {
        setDocument(document);
    };

    const onDocumentRemove = () => {
        setDocument("");
    };

    const getConfig = async () => {
        const token = client ? await getToken(client) : undefined;

        configApi(token).then(config => {
            setShowGPT4VOptions(config.showGPT4VOptions);
            setUseSemanticRanker(config.showSemanticRankerOption);
            setShowSemanticRankerOption(config.showSemanticRankerOption);
            setShowVectorOption(config.showVectorOption);
            if (!config.showVectorOption) {
                setRetrievalMode(RetrievalMode.Text);
            }
        });
    };

    useEffect(() => {
        getConfig();
    }, []);

    const makeApiRequest = async (question: string) => {
        lastQuestionRef.current = question;

        error && setError(undefined);
        setIsLoading(true);

        const token = client ? await getToken(client) : undefined;

        try {
            const request: ChatAppRequest = {
                messages: [
                    {
                        content: question,
                        role: "user"
                    }
                ],
                context: {
                    overrides: {
                        prompt_template: promptTemplate.length === 0 ? undefined : promptTemplate,
                        prompt_template_prefix: promptTemplatePrefix.length === 0 ? undefined : promptTemplatePrefix,
                        prompt_template_suffix: promptTemplateSuffix.length === 0 ? undefined : promptTemplateSuffix,
                        exclude_category: excludeCategory.length === 0 ? undefined : excludeCategory,
                        top: retrieveCount,
                        temperature: temperature,
                        retrieval_mode: retrievalMode,
                        semantic_ranker: useSemanticRanker,
                        semantic_captions: useSemanticCaptions,
                        use_oid_security_filter: useOidSecurityFilter,
                        use_groups_security_filter: useGroupsSecurityFilter,
                        vector_fields: vectorFieldList,
                        use_gpt4v: useGPT4V,
                        gpt4v_input: gpt4vInput
                    }
                },
                // ChatAppProtocol: Client must pass on any session state received from the server
                session_state: answer ? answer.choices[0].session_state : null
            };
            const result = await askApi(request, token);
            setAnswer(result);
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
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

    const onTemperatureChange = (
        newValue: number,
        range?: [number, number],
        event?: React.MouseEvent | React.TouchEvent | MouseEvent | TouchEvent | React.KeyboardEvent
    ) => {
        setTemperature(newValue);
    };

    const onRetrieveCountChange = (_ev?: React.SyntheticEvent<HTMLElement, Event>, newValue?: string) => {
        setRetrieveCount(parseInt(newValue || "3"));
    };

    const onRetrievalModeChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<RetrievalMode> | undefined, index?: number | undefined) => {
        setRetrievalMode(option?.data || RetrievalMode.Hybrid);
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

    const onUseOidSecurityFilterChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseOidSecurityFilter(!!checked);
    };

    const onUseGroupsSecurityFilterChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseGroupsSecurityFilter(!!checked);
    };

    useEffect(() => {
        makeApiRequest("Summarize the following document: " + document);
    }, [document]);

    return (
        <div className={styles.container}>
            {/* <ShowDocuments /> */}

            <section className={styles.mainContent}>
                <div className={styles.summarizeContainer}>
                    <div className={styles.textContainer}>
                        {answer ? (
                            <div className={styles.askQuestionContainer}>
                                <Answer
                                    answer={answer as ChatAppResponse}
                                    question={lastQuestionRef.current}
                                    isStreaming={true}
                                    onCitationClicked={function (filePath: string): void {
                                        throw new Error("Function not implemented.");
                                    }}
                                    onThoughtProcessClicked={function (): void {
                                        throw new Error("Function not implemented.");
                                    }}
                                    onSupportingContentClicked={function (): void {
                                        throw new Error("Function not implemented.");
                                    }}
                                    onEvaluationClicked={function (): void {
                                        throw new Error("Function not implemented.");
                                    }}
                                />
                                <div className={styles.askQuestionInput}>
                                    <QuestionInput
                                        placeholder="Example: What is the conclusion?"
                                        disabled={isLoading}
                                        initQuestion={question}
                                        onSend={question => makeApiRequest(question)}
                                    />
                                </div>
                            </div>
                        ) : (
                            <h1 className={styles.askTitle}>Please Select or Upload a document to start chatting!</h1>
                        )}
                    </div>
                    <div className={styles.citationContainer}>
                        {document ? <SummarizeDocument id={document} onRemove={onDocumentRemove} /> : <SummarizeSelect onDocumentClicked={onDocumentClicked} />}
                    </div>
                </div>
            </section>
        </div>
    );
}
