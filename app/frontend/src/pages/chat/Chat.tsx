import { useRef, useState, useEffect } from "react";
import { Checkbox, Panel, DefaultButton, TextField, SpinButton, Dropdown, IDropdownOption } from "@fluentui/react";
import readNDJSONStream from "ndjson-readablestream";

import styles from "./Chat.module.css";

import { chatApi, RetrievalMode, ChatAppResponse, ChatAppResponseOrError, ChatAppRequest, ChatInput, ResponseMessage } from "../../api";
import { Answer, AnswerError, AnswerLoading } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { UserChatMessage } from "../../components/UserChatMessage";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";
import { useLogin, getToken } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { TokenClaimsDisplay } from "../../components/TokenClaimsDisplay";
import Vimeo from "@vimeo/player";
import VideoPlayerContainer from "./VideoPlayerContainer";
import ChatHeader from "./ChatHeader";
import ExplanationMessage from "./TermsOfService/ExplanationMessage";
import TermsOfService from "./TermsOfService/TermsOfService";

const Chat: React.FC = ({}) => {
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
    const [promptTemplate, setPromptTemplate] = useState<string>("");
    const [retrieveCount, setRetrieveCount] = useState<number>(3);
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(true);
    const [shouldStream, setShouldStream] = useState<boolean>(true);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);
    const [excludeCategory, setExcludeCategory] = useState<string>("");
    const [useSuggestFollowupQuestions, setUseSuggestFollowupQuestions] = useState<boolean>(false);
    const [useOidSecurityFilter, setUseOidSecurityFilter] = useState<boolean>(false);
    const [useGroupsSecurityFilter, setUseGroupsSecurityFilter] = useState<boolean>(false);

    const lastQuestionRef = useRef<string>("");
    const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [isWritingWords, setIsWritingWords] = useState<boolean>(false);
    const [isPlayingVideo, setIsPlayingVideo] = useState<boolean>(false);
    const [isStreaming, setIsStreaming] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();
    const [isFirstRender, setIsFirstRender] = useState<boolean>(true);

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    const [selectedAnswer, setSelectedAnswer] = useState<number>(0);
    const [answers, setAnswers] = useState<{ content: string; clientRole: string; responses: ChatAppResponse[] }[]>([]);
    const [streamedAnswers, setStreamedAnswers] = useState<{ content: string; clientRole: string; responses: ChatAppResponse[] }[]>([]);

    const [chatInput, setChatInput] = useState<ChatInput>({ inputType: "freeText" });

    const playerRef = useRef<Vimeo>();

    const lastApiCallTime = useRef<number>(0);

    const delay = async (timeout: number) => await new Promise((resolve, reject) => setTimeout(resolve, timeout));

    const handleAsyncRequest = async (
        question: string,
        clientRole: string,
        answers: { content: string; clientRole: string; responses: ChatAppResponse[] }[],
        setAnswers: Function,
        responseBody: ReadableStream<any>
    ) => {
        let role: string;
        let answer: string = "";
        let responses: ChatAppResponse[] = [];
        let askResponse: ChatAppResponse = {} as ChatAppResponse;

        const createResponse = (contentAnswer: string): ChatAppResponse => {
            return {
                ...askResponse,
                choices: [{ ...askResponse.choices[0], message: { content: contentAnswer, role: role } }]
            };
        };

        const updateState = (newContent: string) => {
            answer += newContent;
            const latestResponse = createResponse(answer);
            let latestResponses: ChatAppResponse[] = [...responses, latestResponse];
            setStreamedAnswers([...answers, { content: question, clientRole, responses: latestResponses }]);
        };

        function* asyncWordGenerator(str: string) {
            const words = str.split(" ");
            for (const word of words) {
                // Wait for the delay, then yield the word
                yield word;
            }
        }

        try {
            setIsStreaming(true);

            for await (const event of readNDJSONStream(responseBody)) {
                if (event["inputType"]) {
                    setChatInput(event as ChatInput);
                } else if (event["choices"] && event["choices"][0]["context"] && event["choices"][0]["context"]["data_points"]) {
                    event["choices"][0]["message"] = event["choices"][0]["delta"];
                    askResponse = event as ChatAppResponse;
                } else if (event["choices"] && event["choices"][0]["delta"]) {
                    setIsWritingWords(true);
                    const partsWithContent = event["choices"][0]["delta"].filter((part: any) => part["content"]);
                    for (const msg of partsWithContent) {
                        role = msg["role"] ? msg["role"] : askResponse.choices[0].message.role;
                        if (msg["role"] == "assistant") {
                            const timeToWait = 1350 - (Date.now() - lastApiCallTime.current);
                            if (timeToWait > 0) {
                                await delay(timeToWait);
                            }
                            // Animate writing words only for assistant role
                            const sentence = msg["content"];
                            let isFirst = true;
                            for await (let word of asyncWordGenerator(sentence)) {
                                if (!isFirst) {
                                    setIsLoading(false);
                                    word = " " + word;
                                }
                                await delay(100);
                                updateState(word);

                                if (isFirst) {
                                    setIsLoading(false);
                                    isFirst = false;
                                }
                            }
                        }

                        responses.push(createResponse(msg["content"]));
                    }
                    setIsWritingWords(false);
                }
            }
        } finally {
            setIsStreaming(false);
        }
        return responses;
    };

    const client = useLogin ? useMsal().instance : undefined;

    const makeApiRequest = async (question: string, clientRole: string) => {
        lastQuestionRef.current = question;

        error && setError(undefined);
        setIsLoading(true);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);

        const token = client ? await getToken(client) : undefined;

        try {
            const messages: ResponseMessage[] = answers.flatMap(a => [
                { content: a.content, role: a.clientRole },
                ...a.responses.map(b => {
                    return { content: b.choices[0].message.content, role: b.choices[0].message.role };
                })
            ]);

            const request: ChatAppRequest = {
                messages: [...messages, { content: question, role: clientRole }],
                stream: shouldStream,
                context: {
                    overrides: {
                        prompt_template: promptTemplate.length === 0 ? undefined : promptTemplate,
                        exclude_category: excludeCategory.length === 0 ? undefined : excludeCategory,
                        top: retrieveCount,
                        retrieval_mode: retrievalMode,
                        semantic_ranker: useSemanticRanker,
                        semantic_captions: useSemanticCaptions,
                        suggest_followup_questions: useSuggestFollowupQuestions,
                        use_oid_security_filter: useOidSecurityFilter,
                        use_groups_security_filter: useGroupsSecurityFilter
                    }
                },
                // ChatAppProtocol: Client must pass on any session state received from the server
                session_state: answers.length
                    ? answers[answers.length - 1].responses[answers[answers.length - 1].responses.length - 1].choices[0].session_state
                    : null
            };

            lastApiCallTime.current = Date.now();
            const response = await chatApi(request, token?.accessToken);
            if (!response.body) {
                throw Error("No response body");
            }
            if (shouldStream) {
                const thinkingDelay = new Promise((resolve, reject) => setTimeout(resolve, 500));
                const parsedResponse: ChatAppResponse[] = await handleAsyncRequest(question, clientRole, answers, setAnswers, response.body);
                await thinkingDelay;
                setAnswers([...answers, { content: question, clientRole, responses: parsedResponse }]);
            } else {
                // This might not work since support of roled list in server response
                const parsedResponse: ChatAppResponseOrError = await response.json();
                if (response.status > 299 || !response.ok) {
                    throw Error(parsedResponse.error || "Unknown error");
                }
                setAnswers([...answers, { content: question, clientRole, responses: [parsedResponse as ChatAppResponse] }]);
            }
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

    const extractVimeoUrl = (answer: ChatAppResponse): string | undefined => {
        return answer.choices[0].message.role == "vimeo" ? answer.choices[0].message.content : undefined;
    };

    const shouldShowServerResponse = (answer: ChatAppResponse): boolean => {
        const role = answer.choices[0].message.role;
        return role == "assistant" || role == "explanationText";
    };

    const shouldShowClientMessage = (clientRole: string): boolean => {
        return clientRole == "user";
    };

    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" }), [isLoading]);
    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "auto" }), [streamedAnswers]);

    useEffect(() => {
        if (isFirstRender) {
            setIsFirstRender(false);
            const clientId = new URLSearchParams(window.location.search).get("clientid");
            makeApiRequest(clientId == null || clientId == "" ? "כניסה ללא זיהוי משתמש" : clientId, "init");
        }
    }, [isFirstRender]);

    useEffect(() => {
        if (isLoading || isPlayingVideo) {
            return;
        }

        const ans = isStreaming ? streamedAnswers : answers;
        const lastAnswer = ans.length > 0 ? ans[ans.length - 1].responses : undefined;
        const lastRoledAnswer = lastAnswer && lastAnswer.length > 0 ? lastAnswer[lastAnswer.length - 1] : undefined;
        const vimeoUrl = lastRoledAnswer ? extractVimeoUrl(lastRoledAnswer) : undefined;
        if (!vimeoUrl) {
            return;
        }

        setIsPlayingVideo(true);
        playerRef.current = new Vimeo("playerElement", {
            url: vimeoUrl,
            autoplay: true,
            controls: false,
            dnt: true,
            title: false,
            playsinline: false,
            width: 1000
        });

        playerRef.current.on("ended", () => {
            makeApiRequest("הצפיה הסתיימה", "player");
            setIsPlayingVideo(false);
            playerRef.current?.destroy();
        });
    }, [isStreaming, streamedAnswers, answers, isLoading, isPlayingVideo]);

    const onPromptTemplateChange = (_ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setPromptTemplate(newValue || "");
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

    const onShouldStreamChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setShouldStream(!!checked);
    };

    const onExcludeCategoryChanged = (_ev?: React.FormEvent, newValue?: string) => {
        setExcludeCategory(newValue || "");
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

    const lastAnswer = answers[answers.length - 1];
    const lastRole = lastAnswer && lastAnswer.responses && lastAnswer.responses[0]?.choices[0]?.message?.role;
    const isIntroPage = lastRole == "introPage";
    const isTosPage = lastRole == "termsOfServicePage";

    return (
        <>
            <VideoPlayerContainer hidden={!isPlayingVideo} />
            <div style={{ display: isPlayingVideo ? "none" : "flex", flexFlow: "column", height: "100%" }}>
                <ChatHeader />
                {isIntroPage && <ExplanationMessage onButtonClicked={() => makeApiRequest("go-to-tos", "frontend-client")} />}

                {isTosPage && <TermsOfService onButtonClicked={() => makeApiRequest("user-accepted-tos", "frontend-client")} />}

                {!isIntroPage && !isTosPage && answers.length > 0 && (
                    <div className={styles.container}>
                        <div className={styles.chatRoot}>
                            <div className={styles.chatContainer}>
                                <div className={styles.chatMessageStreamContainer}>
                                    <div className={styles.chatMessageStream}>
                                        {isStreaming &&
                                            streamedAnswers.map((streamedAnswer, index) => (
                                                <div key={index}>
                                                    {shouldShowClientMessage(streamedAnswer.clientRole) && <UserChatMessage message={streamedAnswer.content} />}
                                                    {streamedAnswer.responses.map(
                                                        (roledAnswer, index) =>
                                                            shouldShowServerResponse(roledAnswer) && (
                                                                <div key={index} className={styles.chatMessageGpt}>
                                                                    <Answer
                                                                        isStreaming={true}
                                                                        key={index}
                                                                        answer={roledAnswer}
                                                                        isSelected={false}
                                                                        onCitationClicked={c => onShowCitation(c, index)}
                                                                        onThoughtProcessClicked={() => onToggleTab(AnalysisPanelTabs.ThoughtProcessTab, index)}
                                                                        onSupportingContentClicked={() =>
                                                                            onToggleTab(AnalysisPanelTabs.SupportingContentTab, index)
                                                                        }
                                                                        onFollowupQuestionClicked={q => makeApiRequest(q, "user")}
                                                                        showFollowupQuestions={useSuggestFollowupQuestions && answers.length - 1 === index}
                                                                    />
                                                                </div>
                                                            )
                                                    )}
                                                </div>
                                            ))}
                                        {!isStreaming &&
                                            answers.map((answer, index) => (
                                                <div key={index}>
                                                    {shouldShowClientMessage(answer.clientRole) && <UserChatMessage message={answer.content} />}
                                                    {answer.responses.map(
                                                        (roledAnswer, index) =>
                                                            shouldShowServerResponse(roledAnswer) && (
                                                                <div key={index} className={styles.chatMessageGpt}>
                                                                    <Answer
                                                                        isStreaming={false}
                                                                        key={index}
                                                                        answer={roledAnswer}
                                                                        isSelected={selectedAnswer === index && activeAnalysisPanelTab !== undefined}
                                                                        onCitationClicked={c => onShowCitation(c, index)}
                                                                        onThoughtProcessClicked={() => onToggleTab(AnalysisPanelTabs.ThoughtProcessTab, index)}
                                                                        onSupportingContentClicked={() =>
                                                                            onToggleTab(AnalysisPanelTabs.SupportingContentTab, index)
                                                                        }
                                                                        onFollowupQuestionClicked={q => makeApiRequest(q, "user")}
                                                                        showFollowupQuestions={useSuggestFollowupQuestions && answers.length - 1 === index}
                                                                    />
                                                                </div>
                                                            )
                                                    )}
                                                </div>
                                            ))}
                                        {isLoading && (
                                            <div>
                                                <UserChatMessage message={lastQuestionRef.current} />
                                                <div className={styles.chatMessageGptMinWidth}>
                                                    <AnswerLoading />
                                                </div>
                                            </div>
                                        )}
                                        {error ? (
                                            <div>
                                                <UserChatMessage message={lastQuestionRef.current} />
                                                <div className={styles.chatMessageGptMinWidth}>
                                                    <AnswerError error={error.toString()} onRetry={() => makeApiRequest(lastQuestionRef.current, "user")} />
                                                </div>
                                            </div>
                                        ) : null}
                                        <div ref={chatMessageStreamEnd} />
                                    </div>
                                </div>

                                <div className={styles.chatInput}>
                                    <QuestionInput
                                        clearOnSend
                                        disabled={isLoading || isWritingWords || isFirstRender || isPlayingVideo}
                                        chatInput={chatInput}
                                        onSend={question => makeApiRequest(question, "user")}
                                        isLoading={isLoading || isWritingWords}
                                    />
                                </div>
                            </div>

                            {answers.length > 0 && activeAnalysisPanelTab && (
                                <AnalysisPanel
                                    className={styles.chatAnalysisPanel}
                                    activeCitation={activeCitation}
                                    onActiveTabChanged={x => onToggleTab(x, selectedAnswer)}
                                    citationHeight="810px"
                                    answer={answers[selectedAnswer].responses[answers[selectedAnswer].responses.length - 1]}
                                    activeTab={activeAnalysisPanelTab}
                                />
                            )}

                            <Panel
                                headerText="Configure answer generation"
                                isOpen={isConfigPanelOpen}
                                isBlocking={false}
                                onDismiss={() => setIsConfigPanelOpen(false)}
                                closeButtonAriaLabel="Close"
                                onRenderFooterContent={() => <DefaultButton onClick={() => setIsConfigPanelOpen(false)}>Close</DefaultButton>}
                                isFooterAtBottom={true}
                            >
                                <TextField
                                    className={styles.chatSettingsSeparator}
                                    defaultValue={promptTemplate}
                                    label="Override prompt template"
                                    multiline
                                    autoAdjustHeight
                                    onChange={onPromptTemplateChange}
                                />

                                <SpinButton
                                    className={styles.chatSettingsSeparator}
                                    label="Retrieve this many search results:"
                                    min={1}
                                    max={50}
                                    defaultValue={retrieveCount.toString()}
                                    onChange={onRetrieveCountChange}
                                />
                                <TextField className={styles.chatSettingsSeparator} label="Exclude category" onChange={onExcludeCategoryChanged} />
                                <Checkbox
                                    className={styles.chatSettingsSeparator}
                                    checked={useSemanticRanker}
                                    label="Use semantic ranker for retrieval"
                                    onChange={onUseSemanticRankerChange}
                                />
                                <Checkbox
                                    className={styles.chatSettingsSeparator}
                                    checked={useSemanticCaptions}
                                    label="Use query-contextual summaries instead of whole documents"
                                    onChange={onUseSemanticCaptionsChange}
                                    disabled={!useSemanticRanker}
                                />
                                <Checkbox
                                    className={styles.chatSettingsSeparator}
                                    checked={useSuggestFollowupQuestions}
                                    label="Suggest follow-up questions"
                                    onChange={onUseSuggestFollowupQuestionsChange}
                                />
                                {useLogin && (
                                    <Checkbox
                                        className={styles.chatSettingsSeparator}
                                        checked={useOidSecurityFilter}
                                        label="Use oid security filter"
                                        disabled={!client?.getActiveAccount()}
                                        onChange={onUseOidSecurityFilterChange}
                                    />
                                )}
                                {useLogin && (
                                    <Checkbox
                                        className={styles.chatSettingsSeparator}
                                        checked={useGroupsSecurityFilter}
                                        label="Use groups security filter"
                                        disabled={!client?.getActiveAccount()}
                                        onChange={onUseGroupsSecurityFilterChange}
                                    />
                                )}
                                <Dropdown
                                    className={styles.chatSettingsSeparator}
                                    label="Retrieval mode"
                                    options={[
                                        {
                                            key: "hybrid",
                                            text: "Vectors + Text (Hybrid)",
                                            selected: retrievalMode == RetrievalMode.Hybrid,
                                            data: RetrievalMode.Hybrid
                                        },
                                        { key: "vectors", text: "Vectors", selected: retrievalMode == RetrievalMode.Vectors, data: RetrievalMode.Vectors },
                                        { key: "text", text: "Text", selected: retrievalMode == RetrievalMode.Text, data: RetrievalMode.Text }
                                    ]}
                                    required
                                    onChange={onRetrievalModeChange}
                                />
                                <Checkbox
                                    className={styles.chatSettingsSeparator}
                                    checked={shouldStream}
                                    label="Stream chat completion responses"
                                    onChange={onShouldStreamChange}
                                />
                                {useLogin && <TokenClaimsDisplay />}
                            </Panel>
                        </div>
                    </div>
                )}
            </div>
        </>
    );
};

export default Chat;
