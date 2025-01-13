import { useRef, useState, useEffect, useContext } from "react";
import { Checkbox, Panel, DefaultButton, TextField, ITextFieldProps, ICheckboxProps } from "@fluentui/react";
import { SparkleFilled } from "@fluentui/react-icons";
import { useId } from "@fluentui/react-hooks";
import readNDJSONStream from "ndjson-readablestream";
import ReCAPTCHA from "react-google-recaptcha";

import styles from "./Chat.module.css";
import Modal from "../../components/DislaimerModal/Modal";

import {
    chatApi,
    configApi,
    RetrievalMode,
    ChatAppResponse,
    ChatAppResponseOrError,
    ChatAppRequest,
    ResponseMessage,
    VectorFieldOptions,
    GPT4VInput,
    SpeechConfig
} from "../../api";
import { Answer, AnswerError, AnswerLoading } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example";
import { UserChatMessage } from "../../components/UserChatMessage";
import { HelpCallout } from "../../components/HelpCallout";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";
import { ClearChatButton } from "../../components/ClearChatButton";
import { useLogin, getToken, requireAccessControl } from "../../authConfig";
import { VectorSettings } from "../../components/VectorSettings";
import { useMsal } from "@azure/msal-react";
import { TokenClaimsDisplay } from "../../components/TokenClaimsDisplay";
import { GPT4VSettings } from "../../components/GPT4VSettings";
import { toolTipText } from "../../i18n/tooltips.js";
import { LoginContext } from "../../loginContext";
import { stubbedPublicClientApplication } from "@azure/msal-browser";
import DisclaimerModal from "../../components/DislaimerModal/Modal";

const Chat = () => {
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
    const [promptTemplate, setPromptTemplate] = useState<string>("");
    const [temperature, setTemperature] = useState<number>(0);
    const [seed, setSeed] = useState<number | null>(1000);
    const [minimumRerankerScore, setMinimumRerankerScore] = useState<number>(1.5);
    const [minimumSearchScore, setMinimumSearchScore] = useState<number>(0.02);
    const [retrieveCount, setRetrieveCount] = useState<number>(8);
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(true);
    const [shouldStream, setShouldStream] = useState<boolean>(true);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);
    const [includeCategory, setIncludeCategory] = useState<string>(""); //This is where you set the category that is searched for
    const [excludeCategory, setExcludeCategory] = useState<string>("");
    const [useSuggestFollowupQuestions, setUseSuggestFollowupQuestions] = useState<boolean>(true);
    const [vectorFieldList, setVectorFieldList] = useState<VectorFieldOptions[]>([VectorFieldOptions.Embedding]);
    const [useOidSecurityFilter, setUseOidSecurityFilter] = useState<boolean>(false);
    const [useGroupsSecurityFilter, setUseGroupsSecurityFilter] = useState<boolean>(false);
    const [gpt4vInput, setGPT4VInput] = useState<GPT4VInput>(GPT4VInput.TextAndImages);
    const [useGPT4V, setUseGPT4V] = useState<boolean>(false);

    const lastQuestionRef = useRef<string>("");
    const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [isStreaming, setIsStreaming] = useState<boolean>(true);
    const [error, setError] = useState<unknown>();

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    const [selectedAnswer, setSelectedAnswer] = useState<number>(0);
    const [answers, setAnswers] = useState<[user: string, response: ChatAppResponse][]>([]);
    const [streamedAnswers, setStreamedAnswers] = useState<[user: string, response: ChatAppResponse][]>([]);
    const [speechUrls, setSpeechUrls] = useState<(string | null)[]>([]);

    const [showGPT4VOptions, setShowGPT4VOptions] = useState<boolean>(false);
    const [showSemanticRankerOption, setShowSemanticRankerOption] = useState<boolean>(false);
    const [showVectorOption, setShowVectorOption] = useState<boolean>(true);
    const [showUserUpload, setShowUserUpload] = useState<boolean>(false);
    const [showSpeechInput, setShowSpeechInput] = useState<boolean>(true);
    const [showSpeechOutputBrowser, setShowSpeechOutputBrowser] = useState<boolean>(false);
    const [showSpeechOutputAzure, setShowSpeechOutputAzure] = useState<boolean>(false);
    const audio = useRef(new Audio()).current;
    const [isPlaying, setIsPlaying] = useState(false);

    const [originalUserMessages, setOriginalUserMessages] = useState<string[]>([]);

    const speechConfig: SpeechConfig = {
        speechUrls,
        setSpeechUrls,
        audio,
        isPlaying,
        setIsPlaying
    };

    const getConfig = async () => {
        configApi().then(config => {
            setShowGPT4VOptions(config.showGPT4VOptions);
            setUseSemanticRanker(config.showSemanticRankerOption);
            setShowSemanticRankerOption(config.showSemanticRankerOption);
            setShowVectorOption(config.showVectorOption);
            if (!config.showVectorOption) {
                setRetrievalMode(RetrievalMode.Text);
            }
            setShowUserUpload(config.showUserUpload);
            setShowSpeechInput(config.showSpeechInput);
            setShowSpeechOutputBrowser(config.showSpeechOutputBrowser);
            setShowSpeechOutputAzure(config.showSpeechOutputAzure);
        });
    };

    const handleAsyncRequest = async (question: string, answers: [string, ChatAppResponse][], responseBody: ReadableStream<any>) => {
        let answer: string = "";
        let askResponse: ChatAppResponse = {} as ChatAppResponse;
        let isBlocked = false;
        let isModified = false;
        let truncateHistory = false;
        let modifiedMessage = "";

        const updateState = (newContent: string, role: string | undefined) => {
            return new Promise(resolve => {
                setTimeout(() => {
                    answer += newContent;
                    const latestResponse: ChatAppResponse = {
                        ...askResponse,
                        message: { content: answer, role: role ?? askResponse.message?.role }
                    };
                    if (isBlocked) {
                        setStreamedAnswers([...answers, ["message blocked", latestResponse]]);
                    } else if (isModified) {
                        setStreamedAnswers([...answers, [modifiedMessage || question, latestResponse]]);
                    } else if (truncateHistory) {
                        setStreamedAnswers([[question, latestResponse]]);
                    } else {
                        setStreamedAnswers([...answers, [question, latestResponse]]);
                    }
                    resolve(null);
                }, 33);
            });
        };

        try {
            setIsStreaming(true);
            for await (const event of readNDJSONStream(responseBody)) {
                if (event["action"] === "block") {
                    isBlocked = true;
                    continue;
                } else if (event["action"] === "truncate_history") {
                    truncateHistory = true;
                    continue;
                } else if (event["action"] === "continue_with_modified_input") {
                    isModified = true;
                    continue;
                } else if (event.context?.action === "continue_with_modified_input" && event.context?.modified_message) {
                    modifiedMessage = event.context.modified_message;
                }
                
                if (event["context"] && event["context"]["data_points"]) {
                    event["message"] = event["delta"];
                    askResponse = event as ChatAppResponse;
                } else if (event["delta"] && event["delta"]["content"]) {
                    setIsLoading(false);
                    if (!askResponse.message) {
                        event["message"] = event["delta"];
                        askResponse = event as ChatAppResponse;
                    }
                    await updateState(event["delta"]["content"], event["delta"]["role"]);
                } else if (event["context"]) {
                    askResponse.context = { ...askResponse.context, ...event["context"] };
                } else if (event["error"]) {
                    throw Error(event["error"]);
                }
            }
        } finally {
            const currentStreamedResponse: ChatAppResponse = {
                ...askResponse,
                message: { 
                    content: answer,
                    role: askResponse.message?.role 
                }
            };

            if (!isBlocked && !isModified) {
                if (truncateHistory) {
                    setOriginalUserMessages([originalUserMessages[originalUserMessages.length - 1]]);
                    setStreamedAnswers([[question, currentStreamedResponse]]);
                } else {
                    setStreamedAnswers([...answers, [question, currentStreamedResponse]]);
                }
            }

            if (answer && !isBlocked && !isModified && !truncateHistory) {
                try {
                    const token = client ? await getToken(client) : undefined;
                    const validationResponse = await chatApi(
                        {
                            messages: [
                                ...answers.flatMap(a => [
                                    { content: a[0], role: "user" },
                                    { content: a[1].message.content, role: "assistant" }
                                ]),
                                { content: question, role: "user" },
                                { content: answer, role: "assistant" }
                            ],
                            context: {
                                validate_only: true,
                                overrides: {
                                    vector_fields: vectorFieldList
                                }
                            },
                            session_state: null
                        },
                        false,
                        token
                    );

                    if (validationResponse.ok) {
                        const validationData = await validationResponse.json();
                        if (validationData.context?.validation_failed) {
                            if (validationData.context.action === "truncate_history") {
                                truncateHistory = true;
                                answer = validationData.message.content || "Chat history has been cleared due to content validation";
                                const validationResponse: ChatAppResponse = {
                                    ...askResponse,
                                    message: { content: answer, role: "assistant" }
                                };
                                setOriginalUserMessages([originalUserMessages[originalUserMessages.length - 1]]);
                                setStreamedAnswers([[question, validationResponse]]);
                            }
                        }
                    }
                } catch (error) {
                    console.error("Validation request failed:", error);
                }
            }

            const fullResponse: ChatAppResponse = {
                ...askResponse,
                message: { 
                    content: answer,
                    role: askResponse.message?.role 
                }
            };

            if (truncateHistory) {
                setOriginalUserMessages([originalUserMessages[originalUserMessages.length - 1]]);
                setAnswers([[question, fullResponse]]);
                setStreamedAnswers([[question, fullResponse]]);
            } else {
                if (isBlocked) {
                    setAnswers([...answers, ["message blocked", fullResponse]]);
                } else if (isModified) {
                    setAnswers([...answers, [modifiedMessage || question, fullResponse]]);
                } else {
                    setAnswers([...answers, [question, fullResponse]]);
                }
            }

            setIsStreaming(false);
            setIsLoading(false);

            return { 
                response: fullResponse, 
                blocked: isBlocked, 
                modified: isModified, 
                truncated: truncateHistory,
                modifiedMessage 
            };
        }
    };

    const client = useLogin ? useMsal().instance : undefined;
    const { loggedIn } = useContext(LoginContext);

    const makeApiRequest = async (question: string, recaptchaToken: string) => {
        lastQuestionRef.current = question;
        setOriginalUserMessages(prev => [...prev, question]);

        error && setError(undefined);
        setIsLoading(true);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);

        const token = client ? await getToken(client) : undefined;

        try {
            const messages: ResponseMessage[] = answers.flatMap(a => [
                { content: a[0], role: "user" },
                { content: a[1].message.content, role: "assistant" }
            ]);

            const request: ChatAppRequest = {
                messages: [...messages, { content: question, role: "user" }],
                context: {
                    overrides: {
                        prompt_template: promptTemplate.length === 0 ? undefined : promptTemplate,
                        include_category: includeCategory.length === 0 ? undefined : includeCategory,
                        exclude_category: excludeCategory.length === 0 ? undefined : excludeCategory,
                        top: retrieveCount,
                        temperature: temperature,
                        minimum_reranker_score: minimumRerankerScore,
                        minimum_search_score: minimumSearchScore,
                        retrieval_mode: retrievalMode,
                        semantic_ranker: useSemanticRanker,
                        semantic_captions: useSemanticCaptions,
                        suggest_followup_questions: useSuggestFollowupQuestions,
                        use_oid_security_filter: useOidSecurityFilter,
                        use_groups_security_filter: useGroupsSecurityFilter,
                        vector_fields: vectorFieldList,
                        use_gpt4v: useGPT4V,
                        gpt4v_input: gpt4vInput,
                        ...(seed !== null ? { seed: seed } : {})
                    }
                },
                session_state: answers.length ? answers[answers.length - 1][1].session_state : null,
                recaptcha_token: recaptchaToken
            };

            const response = await chatApi(request, shouldStream, token);
            if (!response.body) {
                throw Error("No response body");
            }
            if (response.status > 299 || !response.ok) {
                throw Error(`Request failed with status ${response.status}`);
            }

            if (shouldStream) {
                const { response: parsedResponse, blocked, modified, truncated, modifiedMessage } = await handleAsyncRequest(question, answers, response.body);
                if (truncated) {
                    setAnswers([[question, parsedResponse]]);
                } else if (!blocked && !modified) {
                    setAnswers([...answers, [question, parsedResponse]]);
                } else if (modified) {
                    setAnswers([...answers, [modifiedMessage || question, parsedResponse]]);
                }
            } else {
                const parsedResponse: ChatAppResponseOrError = await response.json();
                if (parsedResponse.error) {
                    throw Error(parsedResponse.error);
                } else {
                    setAnswers([...answers, [question, parsedResponse as ChatAppResponse]]);
                }
            }
            setSpeechUrls([...speechUrls, null]);
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

    const clearChat = () => {
        lastQuestionRef.current = "";
        error && setError(undefined);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);
        setAnswers([]);
        setOriginalUserMessages([]);
        setSpeechUrls([]);
        setStreamedAnswers([]);
        setIsLoading(false);
        setIsStreaming(false);
    };

    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" }), [isLoading]);
    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "auto" }), [streamedAnswers]);
    useEffect(() => {
        getConfig();
    }, []);

    const onPromptTemplateChange = (_ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setPromptTemplate(newValue || "");
    };

    const onTemperatureChange = (_ev?: React.SyntheticEvent<HTMLElement, Event>, newValue?: string) => {
        setTemperature(parseFloat(newValue || "0"));
    };

    const onSeedChange = (_ev?: React.SyntheticEvent<HTMLElement, Event>, newValue?: string) => {
        setSeed(parseInt(newValue || ""));
    };

    const onMinimumSearchScoreChange = (_ev?: React.SyntheticEvent<HTMLElement, Event>, newValue?: string) => {
        setMinimumSearchScore(parseFloat(newValue || "0.02"));
    };

    const onMinimumRerankerScoreChange = (_ev?: React.SyntheticEvent<HTMLElement, Event>, newValue?: string) => {
        setMinimumRerankerScore(parseFloat(newValue || "1.5"));
    };

    const onRetrieveCountChange = (_ev?: React.SyntheticEvent<HTMLElement, Event>, newValue?: string) => {
        setRetrieveCount(parseInt(newValue || "5"));
    };

    const onUseSemanticRankerChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSemanticRanker(!!checked);
    };

    const onUseSemanticCaptionsChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSemanticCaptions(!!checked);
    };

    const onShouldStreamChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setShouldStream(!!checked);
    };

    const onUseSuggestFollowupQuestionsChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSuggestFollowupQuestions(!!checked);
    };

    const onUseOidSecurityFilterChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseOidSecurityFilter(!!checked);
    };

    const onUseGroupsSecurityFilterChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseGroupsSecurityFilter(!!checked);
    };

    const onExampleClicked = (example: string, token: string) => {
        makeApiRequest(example, token);
    };

    const onShowCitation = (citation: string, index: number) => {
        if (activeCitation === citation && activeAnalysisPanelTab === AnalysisPanelTabs.CitationTab && selectedAnswer === index) {
            setActiveAnalysisPanelTab(undefined);
        } else {
            setActiveCitation(citation);
            setActiveAnalysisPanelTab(AnalysisPanelTabs.CitationTab);
        }

        setSelectedAnswer(index);
    };

    const onToggleTab = (tab: AnalysisPanelTabs, index: number) => {
        if (activeAnalysisPanelTab === tab && selectedAnswer === index) {
            setActiveAnalysisPanelTab(undefined);
        } else {
            setActiveAnalysisPanelTab(tab);
        }

        setSelectedAnswer(index);
    };

    const recaptchaRef = useRef<ReCAPTCHA>(null);

    // just keep the same naming as prod version but don't need recaptcha
    const handleCaptchaOnClick = async (value: string) => {
        if (recaptchaRef.current) {
            try {
                const token = await recaptchaRef.current.executeAsync();
                if (token) {
                    recaptchaRef.current.reset();
                    makeApiRequest(value, token);
                } else {
                    console.error("reCAPTCHA token is null");
                    alert("reCAPTCHA verification failed. Please try again.");
                }
            } catch (error) {
                console.error("reCAPTCHA execution error:", error);
                alert("reCAPTCHA timed out. Please try again.");
            }
    };

    // IDs for form labels and their associated callouts
    const promptTemplateId = useId("promptTemplate");
    const promptTemplateFieldId = useId("promptTemplateField");
    const temperatureId = useId("temperature");
    const temperatureFieldId = useId("temperatureField");
    const seedId = useId("seed");
    const seedFieldId = useId("seedField");
    const searchScoreId = useId("searchScore");
    const searchScoreFieldId = useId("searchScoreField");
    const rerankerScoreId = useId("rerankerScore");
    const rerankerScoreFieldId = useId("rerankerScoreField");
    const retrieveCountId = useId("retrieveCount");
    const retrieveCountFieldId = useId("retrieveCountField");
    const includeCategoryId = useId("includeCategory");
    const includeCategoryFieldId = useId("includeCategoryField");
    const excludeCategoryId = useId("excludeCategory");
    const excludeCategoryFieldId = useId("excludeCategoryField");
    const semanticRankerId = useId("semanticRanker");
    const semanticRankerFieldId = useId("semanticRankerField");
    const semanticCaptionsId = useId("semanticCaptions");
    const semanticCaptionsFieldId = useId("semanticCaptionsField");
    const suggestFollowupQuestionsId = useId("suggestFollowupQuestions");
    const suggestFollowupQuestionsFieldId = useId("suggestFollowupQuestionsField");
    const useOidSecurityFilterId = useId("useOidSecurityFilter");
    const useOidSecurityFilterFieldId = useId("useOidSecurityFilterField");
    const useGroupsSecurityFilterId = useId("useGroupsSecurityFilter");
    const useGroupsSecurityFilterFieldId = useId("useGroupsSecurityFilterField");
    const shouldStreamId = useId("shouldStream");
    const shouldStreamFieldId = useId("shouldStreamField");

    return (
        <div className={styles.container}>
            <ReCAPTCHA sitekey="6LfMIV4qAAAAAPg4D_EMBKndtGzO6xDlzCO8vQTv" size="invisible" ref={recaptchaRef} />
            <DisclaimerModal />
            <div className={styles.commandsContainer}>
                <ClearChatButton className={styles.commandButton} onClick={clearChat} disabled={!lastQuestionRef.current || isLoading} />
            </div>
            <div className={styles.chatRoot}>
                <div className={styles.chatContainer}>
                    {!lastQuestionRef.current ? (
                        <div className={styles.chatEmptyState}>
                            <img className={styles.responsivelogo} src="/logo.png" aria-hidden="true" aria-label="Chat logo" />
                            <h2 className={styles.chatEmptyStateSubtitle}>
                                Our pilot AI conversation tool. Experience the power of AI generated answers to your small business questions - all grounded on
                                public facing government websites.
                            </h2>
                            <ExampleList onExampleClicked={onExampleClicked} />
                        </div>
                    ) : (
                        <div className={styles.chatMessageStream}>
                            {isStreaming &&
                                streamedAnswers.map((streamedAnswer, index) => (
                                    <div key={index}>
                                        <UserChatMessage message={originalUserMessages[index]} />
                                        <div className={styles.chatMessageGpt}>
                                            <Answer
                                                isStreaming={true}
                                                key={index}
                                                answer={streamedAnswer[1]}
                                                index={index}
                                                speechConfig={speechConfig}
                                                isSelected={false}
                                                onCitationClicked={c => onShowCitation(c, index)}
                                                onThoughtProcessClicked={() => onToggleTab(AnalysisPanelTabs.ThoughtProcessTab, index)}
                                                onSupportingContentClicked={() => onToggleTab(AnalysisPanelTabs.SupportingContentTab, index)}
                                                onFollowupQuestionClicked={q => handleCaptchaOnClick(q)}
                                                showFollowupQuestions={useSuggestFollowupQuestions && answers.length - 1 === index}
                                                showSpeechOutputAzure={showSpeechOutputAzure}
                                                showSpeechOutputBrowser={showSpeechOutputBrowser}
                                            />
                                        </div>
                                    </div>
                                ))}
                            {!isStreaming &&
                                answers.map((answer, index) => (
                                    <div key={index}>
                                        <UserChatMessage message={originalUserMessages[index]} />
                                        <div className={styles.chatMessageGpt}>
                                            <Answer
                                                isStreaming={false}
                                                key={index}
                                                answer={answer[1]}
                                                index={index}
                                                speechConfig={speechConfig}
                                                isSelected={selectedAnswer === index && activeAnalysisPanelTab !== undefined}
                                                onCitationClicked={c => onShowCitation(c, index)}
                                                onThoughtProcessClicked={() => onToggleTab(AnalysisPanelTabs.ThoughtProcessTab, index)}
                                                onSupportingContentClicked={() => onToggleTab(AnalysisPanelTabs.SupportingContentTab, index)}
                                                onFollowupQuestionClicked={q => handleCaptchaOnClick(q)}
                                                showFollowupQuestions={useSuggestFollowupQuestions && answers.length - 1 === index}
                                                showSpeechOutputAzure={showSpeechOutputAzure}
                                                showSpeechOutputBrowser={showSpeechOutputBrowser}
                                            />
                                        </div>
                                    </div>
                                ))}
                            {isLoading && (
                                <>
                                    <UserChatMessage message={lastQuestionRef.current} />
                                    <div className={styles.chatMessageGptMinWidth}>
                                        <AnswerLoading />
                                    </div>
                                </>
                            )}
                            {error ? (
                                <>
                                    <UserChatMessage message={lastQuestionRef.current} />
                                    <div className={styles.chatMessageGptMinWidth}>
                                        <AnswerError error={error.toString()} onRetry={() => handleCaptchaOnClick(lastQuestionRef.current)} />
                                    </div>
                                </>
                            ) : null}
                            <div ref={chatMessageStreamEnd} />
                        </div>
                    )}

                    <div className={styles.chatInput}>
                        <QuestionInput
                            clearOnSend
                            placeholder="Type a new question (e.g. What R&D funding is available for New Zealand businesses?)"
                            disabled={isLoading}
                            onSend={question => handleCaptchaOnClick(question)}
                            showSpeechInput={showSpeechInput}
                        />
                    </div>
                </div>

                {answers.length > 0 && activeAnalysisPanelTab && (
                    <AnalysisPanel
                        className={styles.chatAnalysisPanel}
                        activeCitation={activeCitation}
                        onActiveTabChanged={x => onToggleTab(x, selectedAnswer)}
                        citationHeight="810px"
                        answer={answers[selectedAnswer][1]}
                        activeTab={activeAnalysisPanelTab}
                    />
                )}
            </div>
        </div>
    );
};

export default Chat;
