import { useRef, useState, useEffect, FormEvent } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { Checkbox, Panel, DefaultButton, TextField, SpinButton, IDropdownOption, Dropdown } from "@fluentui/react";
import {
    useId,
    Dropdown as DropdownComponent,
    Option,
    Button,
    Dialog,
    DialogTrigger,
    DialogSurface,
    DialogTitle,
    DialogBody,
    DialogActions,
    DialogContent,
    Label,
    Input,
    Spinner,
    Switch
} from "@fluentui/react-components";
import { SparkleFilled } from "@fluentui/react-icons";
import readNDJSONStream from "ndjson-readablestream";
import { auth } from "../../";
import type { DropdownProps } from "@fluentui/react-components";
import axios from "axios";
import styles from "./Chat.module.css";

import { chatApi, RetrievalMode, ChatAppResponse, ChatAppResponseOrError, ChatAppRequest, ResponseMessage, runScriptApi } from "../../api";
import { Answer, AnswerError, AnswerLoading } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example";
import { UserChatMessage } from "../../components/UserChatMessage";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";
import { SettingsButton } from "../../components/SettingsButton";
import { ClearChatButton } from "../../components/ClearChatButton";
import { useLogin, getToken } from "../../authConfig";
import { useMsal } from "@azure/msal-react";
import { TokenClaimsDisplay } from "../../components/TokenClaimsDisplay";
import { v4 as uuidv4 } from "uuid";

const Chat = (dropdownProps: Partial<DropdownProps>) => {
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
    const [isStreaming, setIsStreaming] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    const [selectedAnswer, setSelectedAnswer] = useState<number>(0);
    const [answers, setAnswers] = useState<[user: string, response: ChatAppResponse][]>([]);
    const [streamedAnswers, setStreamedAnswers] = useState<[user: string, response: ChatAppResponse][]>([]);
    const [parameters, setParameters] = useState<Record<string, string>>({
        tone: "",
        readability: "",
        wordCount: "",
        communicationFramework: ""
    });
    const [module, setModule] = useState<string>("Chat");
    const [currentProject, setCurrentProject] = useState<string>("default");
    const [projectOptions, setProjectOptions] = useState<ProjectOptions[]>([]);

    const [index, setIndex] = useState<string>("gptkbindex");
    const [container, setContainer] = useState<string>("content");
    // const [savedChats, setSavedChats] = useState<any>([]);
    // const [openSave, setOpenSave] = useState<boolean>(false);
    // const [loadingSaveChat, setLoadingSaveChat] = useState<boolean>(false);
    // const [chatName, setChatName] = useState<string>("");
    const baseURL = import.meta.env.VITE_FIREBASE_BASE_URL;
    // const baseURL = "http://127.0.0.1:5001/projectpalai-83a5f/us-central1/";
    const navigate = useNavigate();
    const dropdownId = useId("dropdown-default");

    const handleAsyncRequest = async (question: string, answers: [string, ChatAppResponse][], setAnswers: Function, responseBody: ReadableStream<any>) => {
        let answer: string = "";
        let askResponse: ChatAppResponse = {} as ChatAppResponse;

        const updateState = (newContent: string) => {
            return new Promise(resolve => {
                setTimeout(() => {
                    answer += newContent;
                    const latestResponse: ChatAppResponse = {
                        ...askResponse,
                        choices: [{ ...askResponse.choices[0], message: { content: answer, role: askResponse.choices[0].message.role } }]
                    };
                    setStreamedAnswers([...answers, [question, latestResponse]]);
                    localStorage.setItem("streamedAnswers", JSON.stringify([...answers, [question, latestResponse]]));
                    resolve(null);
                }, 33);
            });
        };
        try {
            setIsStreaming(true);
            for await (const event of readNDJSONStream(responseBody)) {
                if (event["choices"] && event["choices"][0]["context"] && event["choices"][0]["context"]["data_points"]) {
                    event["choices"][0]["message"] = event["choices"][0]["delta"];
                    askResponse = event as ChatAppResponse;
                } else if (event["choices"] && event["choices"][0]["delta"]["content"]) {
                    setIsLoading(false);
                    await updateState(event["choices"][0]["delta"]["content"]);
                } else if (event["choices"] && event["choices"][0]["context"]) {
                    // Update context with new keys from latest event
                    askResponse.choices[0].context = { ...askResponse.choices[0].context, ...event["choices"][0]["context"] };
                } else if (event["error"]) {
                    throw Error(event["error"]);
                }
            }
        } finally {
            setIsStreaming(false);
        }
        const fullResponse: ChatAppResponse = {
            ...askResponse,
            choices: [{ ...askResponse.choices[0], message: { content: answer, role: askResponse.choices[0].message.role } }]
        };
        return fullResponse;
    };

    const client = useLogin ? useMsal().instance : undefined;

    const makeApiRequest = async (question: string) => {
        lastQuestionRef.current = question;
        let questionWithParameters = question;
        if (module === "Content Creation") {
            const toneString = parameters.tone === "" ? "" : `Respond in a tone that is ${parameters.tone}.`;
            const readabilityString =
                parameters.readability === ""
                    ? ""
                    : `The readability of the response should be of ${parameters.readability} readability, using a Flesch-Kincaid approach.`;
            const wordCountString =
                parameters.wordCount === "" ? "" : `Make absolutely certain that your answer does not exceed ${parameters.wordCount} words.`;
            const communicationFrameworkString =
                parameters.communicationFramework === ""
                    ? ""
                    : `The communication framework for the response should utilize a ${parameters.communicationFramework} model.`;

            const parameterString = `${toneString} ${readabilityString} ${wordCountString} ${communicationFrameworkString}`;
            questionWithParameters = question + ". Respond using the following rules: " + parameterString + ".";
        }

        error && setError(undefined);
        setIsLoading(true);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);

        const token = client ? await getToken(client) : undefined;

        try {
            const messages: ResponseMessage[] = answers.flatMap(a => [
                { content: a[0], role: "user" },
                { content: a[1].choices[0].message.content, role: "assistant" }
            ]);

            const request: ChatAppRequest = {
                messages: [...messages, { content: questionWithParameters, role: "user" }],
                azureIndex: index,
                azureContainer: container,
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
                session_state: answers.length ? answers[answers.length - 1][1].choices[0].session_state : null
            };

            //runScriptApi(request, token?.accessToken);

            console.log("Token: " + token?.accessToken);
            const response = await chatApi(request, token?.accessToken);
            if (!response.body) {
                throw Error("No response body");
            }
            if (shouldStream) {
                const parsedResponse: ChatAppResponse = await handleAsyncRequest(question, answers, setAnswers, response.body);
                console.log(streamedAnswers);
                setAnswers([...answers, [question, parsedResponse]]);
            } else {
                const parsedResponse: ChatAppResponseOrError = await response.json();
                if (response.status > 299 || !response.ok) {
                    throw Error(parsedResponse.error || "Unknown error");
                }
                setAnswers([...answers, [question, parsedResponse as ChatAppResponse]]);
            }
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
        setStreamedAnswers([]);
        setIsLoading(false);
        setIsStreaming(false);
    };

    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" }), [isLoading]);
    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "auto" }), [streamedAnswers]);

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

    const onExampleClicked = (example: string) => {
        makeApiRequest(example);
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

    const handleSetProject = (project: string) => {
        if (project === currentProject) {
            return;
        }
        setAnswers([]);
        setStreamedAnswers([]);
        lastQuestionRef.current = "";
        const projectOption = projectOptions.find(p => p.projectName === project);
        if (projectOption) {
            setIndex(projectOption.projectIndex);
            setContainer(projectOption.projectContainer);
            setCurrentProject(project);
        }
    };

    const toneOptions = ["Formal", "Informal", "Motivational", "Celebratory", "Cautious"];

    const readabilityOptions = ["Low", "Medium", "High"];

    const wordCountOptions = ["100", "200", "300"];

    const communicationFrameworkOptions = ["Think/Feel/Do", "Before/During/After", "Concentric Circles"];

    const handleSetAnswersFromStreamed = () => {
        if (localStorage.getItem("streamedAnswers")) {
            setAnswers(JSON.parse(localStorage.getItem("streamedAnswers") || ""));
            const streamedAnswers = localStorage.getItem("streamedAnswers");
            if (streamedAnswers) {
                lastQuestionRef.current = JSON.parse(streamedAnswers)[0][0] || "";
            }
        }
    };

    const handleSwitchModule = () => {
        clearChat();
        if (module === "Chat") {
            setModule("Content Creation");
        } else {
            setModule("Chat");
        }
    };
    // const openSaveChatDialog = () => {
    //     setOpenSave(true);
    // };

    // const handleSaveChat = (event: FormEvent<HTMLFormElement>) => {
    //     event.preventDefault();

    //     const request = {
    //         userUid: auth.currentUser?.uid,
    //         chatName: chatName,
    //         answers: answers,
    //         project: currentProject,
    //         date: new Date().toISOString(),
    //         id: uuidv4()
    //     };
    //     axios.post(baseURL + "saveChatMessage", { request }).then(response => {
    //         setLoadingSaveChat(false);
    //         setOpenSave(false);
    //         setSavedChats([...savedChats, [chatName, answers]]);
    //     });
    // };

    // const loadChat = (chatId: string) => {};
    useEffect(() => {
        if (!auth.currentUser) {
            navigate("/login");
        } else {
            // if (localStorage.getItem("user")) {
            //     const userString = localStorage.getItem("user");
            //     if (userString) {
            //         const user = JSON.parse(userString);
            //         if (user.chats) {
            //             setSavedChats(user.chats);
            //         }
            //     }
            // }

            const projectString = localStorage.getItem("projects");
            if (projectString) {
                const projects = JSON.parse(projectString);
                let compArray: ProjectOptions[] = [];
                projects.forEach((project: Project) => {
                    // console.log("PROJECT", project)
                    compArray.push({
                        projectName: project.projectName ?? "",
                        projectIndex: project.projectIndex ?? project.projectID ?? "",
                        projectContainer: project.projectContainer ?? project.projectID ?? ""
                    });
                });
                setProjectOptions(compArray);
                setCurrentProject(compArray[0].projectName);
                setIndex(compArray[0].projectIndex);
                setContainer(compArray[0].projectContainer);
            }
        }
    }, []);
    return (
        <div className={styles.container}>
            <div className={styles.chatRoot}>
                <div className={styles.chatContainer}>
                    {/* {savedChats && <div className={styles.savedChats}>Saved chats</div>}


                    <Dialog open={openSave} onOpenChange={(_, data) => setOpenSave(data.open)}>
                        <DialogSurface style={{ maxWidth: "400px" }}>
                            <DialogBody
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    flexDirection: "column"
                                }}
                            >
                                <DialogTitle>Save current chat</DialogTitle>
                                <form onSubmit={handleSaveChat} style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                                    <DialogContent>
                                        <div className={`${styles.inputColumn} ${styles.edit}`}>
                                            <div className={styles.inputGroup}>
                                                <Label>Chat Name</Label>
                                                <Input
                                                    name="chatName"
                                                    placeholder="Chat name"
                                                    aria-label="Chat name"
                                                    onChange={e => setChatName(e.target.value)}
                                                    required
                                                />
                                                {loadingSaveChat && <Spinner label="Loading..." labelPosition="below" size="large" />}
                                            </div>
                                        </div>
                                    </DialogContent>
                                    <DialogActions style={{ justifyContent: "space-between" }}>
                                        <DialogTrigger disableButtonEnhancement>
                                            <Button appearance="secondary">Close</Button>
                                        </DialogTrigger>
                                        <Button appearance="primary" type="submit" disabled={loadingSaveChat}>
                                            Save chat
                                        </Button>
                                    </DialogActions>
                                </form>
                            </DialogBody>
                        </DialogSurface>
                    </Dialog> */}
                    <div className={styles.chatRow}>
                        <div className={styles.chatColumn}>
                            {!lastQuestionRef.current ? (
                                <div className={styles.chatEmptyState}>
                                    <h1 className={styles.chatEmptyStateTitle}>
                                        {module === "Chat" ? "Chat with your project data" : "Create content for your project"}
                                    </h1>
                                    <h2 className={styles.chatEmptyStateSubtitle}>Ask anything or try one of these examples</h2>
                                    <ExampleList onExampleClicked={onExampleClicked} module={module} />
                                </div>
                            ) : (
                                <div className={styles.chatMessageStream}>
                                    {isStreaming &&
                                        streamedAnswers.map((streamedAnswer, index) => (
                                            <div key={index}>
                                                <UserChatMessage message={streamedAnswer[0]} />
                                                <div className={styles.chatMessageGpt}>
                                                    <Answer
                                                        isStreaming={true}
                                                        key={index}
                                                        answer={streamedAnswer[1]}
                                                        isSelected={false}
                                                        onCitationClicked={c => onShowCitation(c, index)}
                                                        onThoughtProcessClicked={() => onToggleTab(AnalysisPanelTabs.ThoughtProcessTab, index)}
                                                        onSupportingContentClicked={() => onToggleTab(AnalysisPanelTabs.SupportingContentTab, index)}
                                                        onFollowupQuestionClicked={q => makeApiRequest(q)}
                                                        showFollowupQuestions={useSuggestFollowupQuestions && answers.length - 1 === index}
                                                    />
                                                </div>
                                            </div>
                                        ))}

                                    {!isStreaming &&
                                        answers.map((answer, index) => (
                                            <div key={index}>
                                                <UserChatMessage message={answer[0]} />
                                                <div className={styles.chatMessageGpt}>
                                                    <Answer
                                                        isStreaming={false}
                                                        key={index}
                                                        answer={answer[1]}
                                                        isSelected={selectedAnswer === index && activeAnalysisPanelTab !== undefined}
                                                        onCitationClicked={c => onShowCitation(c, index)}
                                                        onThoughtProcessClicked={() => onToggleTab(AnalysisPanelTabs.ThoughtProcessTab, index)}
                                                        onSupportingContentClicked={() => onToggleTab(AnalysisPanelTabs.SupportingContentTab, index)}
                                                        onFollowupQuestionClicked={q => makeApiRequest(q)}
                                                        showFollowupQuestions={useSuggestFollowupQuestions && answers.length - 1 === index}
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
                                                <AnswerError error={error.toString()} onRetry={() => makeApiRequest(lastQuestionRef.current)} />
                                            </div>
                                        </>
                                    ) : null}
                                    <div ref={chatMessageStreamEnd} />
                                </div>
                            )}

                            <div className={styles.chatInput}>
                                <QuestionInput
                                    clearOnSend
                                    placeholder="Who is the project sponsor?"
                                    disabled={isLoading}
                                    onSend={question => makeApiRequest(question)}
                                />
                            </div>
                        </div>
                        <div style={{ width: "122px", overflowInline: "hidden" }}>
                            <Switch label={module} labelPosition={"above"} onClick={handleSwitchModule} />
                        </div>
                    </div>
                    {/* {lastQuestionRef.current && <Button onClick={openSaveChatDialog}>Save current Chat</Button>} */}
                    <div className={styles.parameterContainer}>
                        {lastQuestionRef.current && <Button onClick={clearChat}>Clear chat</Button>}
                        {localStorage.getItem("streamedAnswers") && <Button onClick={handleSetAnswersFromStreamed}>View previous chat</Button>}
                    </div>
                    {module === "Content Creation" && (
                        <div className={styles.parameterContainer}>
                            <div className={styles.parameterColumn}>
                                <h2 style={{ color: "#409ece" }}>Tone</h2>
                                <DropdownComponent
                                    style={{ minWidth: "200px" }}
                                    name="toneDropdown"
                                    aria-labelledby={dropdownId}
                                    defaultValue="Select an option"
                                    // defaultSelectedOptions={["Formal"]}
                                    onOptionSelect={(_, selected) => setParameters({ ...parameters, tone: selected.optionValue || "" })}
                                    {...dropdownProps}
                                >
                                    {toneOptions.map(option => (
                                        <Option key={option} text={option} value={option}>
                                            {option}
                                        </Option>
                                    ))}
                                </DropdownComponent>
                            </div>
                            <div className={styles.parameterColumn}>
                                <h2 style={{ color: "#409ece" }}>Readability</h2>
                                <DropdownComponent
                                    style={{ minWidth: "200px" }}
                                    name="readabilityDropdown"
                                    aria-labelledby={dropdownId}
                                    defaultValue="Select an option"
                                    // defaultSelectedOptions={["Medium"]}
                                    onOptionSelect={(_, selected) => setParameters({ ...parameters, readability: selected.optionValue || "" })}
                                    {...dropdownProps}
                                >
                                    {readabilityOptions.map(option => (
                                        <Option key={option} text={option} value={option}>
                                            {option}
                                        </Option>
                                    ))}
                                </DropdownComponent>
                            </div>
                            <div className={styles.parameterColumn}>
                                <h2 style={{ color: "#409ece" }}>Word count</h2>
                                <DropdownComponent
                                    style={{ minWidth: "200px" }}
                                    name="wordCountDropdown"
                                    aria-labelledby={dropdownId}
                                    defaultValue="Select an option"
                                    // defaultSelectedOptions={["200"]}
                                    onOptionSelect={(_, selected) => setParameters({ ...parameters, wordCount: selected.optionValue || "" })}
                                    {...dropdownProps}
                                >
                                    {wordCountOptions.map(option => (
                                        <Option key={option} text={option} value={option}>
                                            {option}
                                        </Option>
                                    ))}
                                </DropdownComponent>
                            </div>
                            <div className={styles.parameterColumn}>
                                <h2 style={{ color: "#409ece" }}>Communication framework</h2>
                                <DropdownComponent
                                    style={{ minWidth: "200px" }}
                                    name="communicationFramewrokDropdown"
                                    aria-labelledby={dropdownId}
                                    defaultValue="Select an option"
                                    // defaultSelectedOptions={["Think/Feel/Do"]}
                                    onOptionSelect={(_, selected) => setParameters({ ...parameters, communicationFramework: selected.optionValue || "" })}
                                    {...dropdownProps}
                                >
                                    {communicationFrameworkOptions.map(option => (
                                        <Option key={option} text={option} value={option}>
                                            {option}
                                        </Option>
                                    ))}
                                </DropdownComponent>
                            </div>
                            {projectOptions && projectOptions.length > 1 && (
                                <div className={styles.parameterColumn}>
                                    <h2 style={{ color: "#409ece" }}>Select project</h2>
                                    <DropdownComponent
                                        style={{ minWidth: "200px" }}
                                        name="projectDropdown"
                                        aria-labelledby={dropdownId}
                                        defaultValue={projectOptions[0].projectName}
                                        defaultSelectedOptions={[projectOptions[0].projectName]}
                                        onOptionSelect={(_, selected) => handleSetProject(selected.optionValue || "")}
                                        {...dropdownProps}
                                    >
                                        {projectOptions.map(option => (
                                            <Option key={option.projectName} text={option.projectName} value={option.projectName}>
                                                {option.projectName}
                                            </Option>
                                        ))}
                                    </DropdownComponent>
                                </div>
                            )}
                        </div>
                    )}
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
                            { key: "hybrid", text: "Vectors + Text (Hybrid)", selected: retrievalMode == RetrievalMode.Hybrid, data: RetrievalMode.Hybrid },
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
    );
};

export default Chat;
