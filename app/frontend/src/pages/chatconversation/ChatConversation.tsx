import { useRef, useState, useEffect } from "react";
import { Checkbox, Panel, DefaultButton, TextField, SpinButton, PanelType } from "@fluentui/react";
import { SparkleFilled } from "@fluentui/react-icons";

import styles from "./ChatConversation.module.css";

import {
    chatConversationApi,
    conversationApi,
    Approaches,
    AskResponse,
    ChatRequest,
    ChatTurn,
    ConversationRequest,
    ConversationResponse,
    BotFrontendFormat,
    ConversationListResponse
} from "../../api";
import { Answer, AnswerError, AnswerLoading } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ChatConversationExampleList } from "../../components/ChatConversationExample";
import { UserChatMessage } from "../../components/UserChatMessage";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";
import { ConversationListButton, ConversationListRefreshButton, ConversationList } from "../../components/ConversationList";
import { SettingsButton } from "../../components/SettingsButton";
import { ClearChatButton } from "../../components/ClearChatButton";
import { string } from "prop-types";

const ChatConversation = () => {
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
    const [isConversationListPanelOpen, setIsConversationListPanelOpen] = useState(false);
    const [promptTemplate, setPromptTemplate] = useState<string>("");
    const [retrieveCount, setRetrieveCount] = useState<number>(3);
    const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(true);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);
    const [excludeCategory, setExcludeCategory] = useState<string>("");
    const [useSuggestFollowupQuestions, setUseSuggestFollowupQuestions] = useState<boolean>(false);

    const lastQuestionRef = useRef<string>("");
    const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    const [selectedAnswer, setSelectedAnswer] = useState<number>(0);
    const [answers, setAnswers] = useState<[user: string, response: AskResponse][]>([]);

    const [loadConversation, setLoadConveration] = useState<boolean>(false);
    const [currentConversationId, setCurrentConversationId] = useState<string>("");
    const [conversationList, setConversationList] = useState<ConversationListResponse | null>(null);
    const [conversationListFetched, setConversationListFetched] = useState(false);

    //Maps the response from conversations and messages to be rendered in the chat window
    const renderConverationMessageHistory = (mylist: BotFrontendFormat) => {
        return mylist.map(
            ({ user, bot }, index) =>
                [
                    user,
                    {
                        answer: bot,
                        thoughts: null,
                        data_points: [],
                        conversation_id: ""
                    }
                ] as [string, AskResponse]
        );
    };

    async function getConversationMessages(conversation_id: string) {
        setIsLoading(true);
        try {
            const request: ConversationRequest = {
                conversation_id: conversation_id,
                baseroute: "/conversation",
                route: "/read",
                approach: Approaches.ChatConversation
            };
            const result = await conversationApi(request);
            return result;
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    }

    // list all the conversations for the user
    async function listConversations() {
        try {
            const request: ConversationRequest = {
                baseroute: "/conversation",
                route: "/list"
            };
            const result: ConversationListResponse = await conversationApi(request);
            return result;
        } catch (e) {
            setError(e);
        } finally {
        }
    }

    const makeApiRequest = async (question: string) => {
        lastQuestionRef.current = question;

        error && setError(undefined);
        setIsLoading(true);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);

        try {
            const history: ChatTurn[] = answers.map(a => ({ user: a[0], bot: a[1].answer }));
            const request: ChatRequest = {
                history: [...history, { user: question, bot: undefined }],
                // Change the approach here to route to GPT model
                approach: Approaches.ChatConversation,
                overrides: {
                    promptTemplate: promptTemplate.length === 0 ? undefined : promptTemplate,
                    excludeCategory: excludeCategory.length === 0 ? undefined : excludeCategory,
                    top: retrieveCount,
                    semanticRanker: useSemanticRanker,
                    semanticCaptions: useSemanticCaptions,
                    suggestFollowupQuestions: useSuggestFollowupQuestions
                },
                conversation_id: currentConversationId
            };
            const result = await chatConversationApi(request);
            setAnswers([...answers, [question, result]]);
            setCurrentConversationId(result.conversation_id);
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

    // BDL TODO: WIP need to get the conversation and render it in the chat.
    const renderConversation = () => {
        setCurrentConversationId("acea80d8-a374-415b-80ff-30cd6a3722db");
        getConversationMessages(currentConversationId).then(result => {
            if (result?.messages) {
                let messages = result.messages;
                const formattedAnswers = renderConverationMessageHistory(messages);
                setAnswers(formattedAnswers);
            } else {
                console.log("There were no messages");
                //todo throw an error of some kind here
            }
        });
        lastQuestionRef.current = answers[answers.length - 1][0];
    };
    const clearChat = () => {
        lastQuestionRef.current = "";
        error && setError(undefined);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);
        setAnswers([]);
        setCurrentConversationId("");
    };

    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" }), [isLoading]);

    const onPromptTemplateChange = (_ev?: React.FormEvent<HTMLInputElement | HTMLTextAreaElement>, newValue?: string) => {
        setPromptTemplate(newValue || "");
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

    const onUseSuggestFollowupQuestionsChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSuggestFollowupQuestions(!!checked);
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

    const refreshConversationList = () => {
        listConversations().then(result => {
            setConversationList(result || null);
        });
    };

    const handleConversationListButtonClick = () => {
        setIsConversationListPanelOpen(!isConversationListPanelOpen);
        listConversations().then(result => {
            setConversationList(result || null);
            setConversationListFetched(true); // Set this state to trigger the useEffect
        });
    };

    useEffect(() => {
        if (conversationListFetched) {
            console.log("Here's your list of conversations", conversationList);
        }
    }, [conversationListFetched]); // Run the effect when conversationListFetched changes

    return (
        <div className={styles.container}>
            <div className={styles.commandsContainer}>
                <ConversationListButton className={styles.commandButtonLeft} onClick={handleConversationListButtonClick} />
                <ClearChatButton className={styles.commandButtonRight} onClick={clearChat} disabled={!lastQuestionRef.current || isLoading} />
                <SettingsButton className={styles.commandButtonRight} onClick={() => setIsConfigPanelOpen(!isConfigPanelOpen)} />
            </div>
            <div className={styles.chatRoot}>
                <div className={styles.chatContainer}>
                    {!lastQuestionRef.current ? (
                        <div className={styles.chatEmptyState}>
                            {/* <SparkleFilled fontSize={"120px"} primaryFill={"rgba(115, 118, 225, 1)"} aria-hidden="true" aria-label="Chat logo" />
                            <h1 className={styles.chatEmptyStateTitle}>Chat with your data</h1>
                            <h2 className={styles.chatEmptyStateSubtitle}>Ask anything or try an example</h2>
                            <ExampleList onExampleClicked={onExampleClicked} /> */}
                            <ChatConversationExampleList onExampleClicked={onExampleClicked} />
                        </div>
                    ) : (
                        <div className={styles.chatMessageStream}>
                            {answers.map((answer, index) => (
                                <div key={index}>
                                    <UserChatMessage message={answer[0]} />
                                    <div className={styles.chatMessageGpt}>
                                        <Answer
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
                        <QuestionInput clearOnSend placeholder={"Type a message here."} disabled={isLoading} onSend={question => makeApiRequest(question)} />
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
                        label="Retrieve this many documents from search:"
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
                </Panel>
                <Panel
                    headerText="Conversation List"
                    isOpen={isConversationListPanelOpen}
                    type={PanelType.customNear}
                    customWidth="340px"
                    isBlocking={false}
                    //onOpen={() => listConversations().then(result => setConversationList(result || null))}
                    onDismiss={() => setIsConversationListPanelOpen(false)}
                    closeButtonAriaLabel="Close"
                    onRenderFooterContent={() => <DefaultButton onClick={() => setIsConversationListPanelOpen(false)}>Close</DefaultButton>}
                    isFooterAtBottom={true}
                >
                    <ConversationListRefreshButton className={styles.commandButton} onClick={refreshConversationList} />
                    <p>Conversation List goes here </p>
                    <ConversationList listOfConversations={conversationList} />
                </Panel>
            </div>
        </div>
    );
};

export default ChatConversation;
