// @ts-nocheck
import { useRef, useState, useEffect } from "react";
import { Checkbox, Panel, DefaultButton, TextField, SpinButton, Dropdown, IDropdownOption } from "@fluentui/react";
import { SparkleFilled } from "@fluentui/react-icons";

import helper from "../../assets/helper.svg";
import styles from "./Chat.module.css";

import { chatApi, RetrievalMode, Approaches, AskResponse, ChatRequest, ChatTurn } from "../../api";
import { Answer, AnswerError, AnswerLoading } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example";
import { UserChatMessage } from "../../components/UserChatMessage";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";
import { SettingsButton } from "../../components/SettingsButton";
import { ClearChatButton } from "../../components/ClearChatButton";
import { ProfilePanel } from "../../components/ProfilePanel";
import { FilterPanel } from "../../components/FilterPanel";
import { CustomerProfileButton } from "../../components/CustomerProfileButton";
import { SearchFilterButton } from "../../components/SearchFilterButton";

import { DEFAULT_SYSTEM_PROMPT, DEFAULT_QUERY_PROMPT } from "../../constants";

function removeEmptyAttributes(obj) {
    const result = {};
    for (const key in obj) {
        if (obj.hasOwnProperty(key)) {
            const value = obj[key];
            if (value !== "" && value !== undefined && value !== null) {
                result[key] = value;
            }
        }
    }
    return result;
}

interface CustomerProfile {
    existingCustomer: boolean;
    name: string;
    familyType: string;
    coverType: string;
    ages: string;
    budget: string;
    notes: string;
}

export interface FilterSettings {
    familyType?: string;
    productType?: string;
    stateType?: string;
    lifecycle?: string;
}

const Chat = () => {
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
    const [isProfilePanelOpen, setIsProfilePanelOpen] = useState(false);
    const [isFilterPanelOpen, setIsFilterPanelOpen] = useState(false);
    const [promptTemplate, setPromptTemplate] = useState<string>(DEFAULT_SYSTEM_PROMPT);
    const [searchPromptTemplate, setSearchPromptTemplate] = useState<string>(DEFAULT_QUERY_PROMPT);
    const [customerProfileString, setCustomerProfileString] = useState<string>("");
    const [retrieveCount, setRetrieveCount] = useState<number>(5);
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(true);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);
    const [excludeCategory, setExcludeCategory] = useState<string>("");
    const [useSuggestFollowupQuestions, setUseSuggestFollowupQuestions] = useState<boolean>(false);
    const [filterSettings, setFilterSettings] = useState<FilterSettings>({});
    const [temprature, setTemprature] = useState<string>("0.7");
    const [searchTemprature, setSearchTemprature] = useState<string>("0.0");
    const [searchTokens, setSearchTokens] = useState<string>("32");

    const lastQuestionRef = useRef<string>("");
    const chatMessageStreamEnd = useRef<HTMLDivElement | null>(null);

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    const [selectedAnswer, setSelectedAnswer] = useState<number>(0);
    const [answers, setAnswers] = useState<[user: string, response: AskResponse][]>([]);

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
                approach: Approaches.ReadRetrieveRead,
                overrides: {
                    temperature: parseFloat(temprature),
                    searchTemperature: parseFloat(searchTemprature),
                    searchMaxTokens: parseInt(searchTokens),
                    promptTemplate: promptTemplate.length === 0 ? undefined : promptTemplate,
                    searchPromptTemplate: searchPromptTemplate.length === 0 ? undefined : searchPromptTemplate,
                    excludeCategory: excludeCategory.length === 0 ? undefined : excludeCategory,
                    top: retrieveCount,
                    retrievalMode: retrievalMode,
                    semanticRanker: useSemanticRanker,
                    semanticCaptions: useSemanticCaptions,
                    suggestFollowupQuestions: useSuggestFollowupQuestions
                },
                profile:
                    customerProfileString.length === 0 ? "Actually, no customer has been given. Please inform me if i ask about it." : customerProfileString,
                filters: removeEmptyAttributes(filterSettings)
            };
            const result = await chatApi(request);
            setAnswers([...answers, [question, result]]);
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
    };

    useEffect(() => chatMessageStreamEnd.current?.scrollIntoView({ behavior: "smooth" }), [isLoading]);

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

    const setProfile = profile => {
        const { existingCustomer, state, category, levelOfCover, scale, budget, frequency, geography, notes } = profile;
        let string = "The customer is";

        if (existingCustomer !== undefined) {
            string += ` an ${existingCustomer ? "existing" : "new"} customer`;
        }

        if (scale) {
            string += ` and is a ${scale}`;
        }

        if (state) {
            string += ` from ${state}`;
        }

        if (category) {
            string += ` in the ${category} category`;
        }

        if (levelOfCover) {
            string += ` with a level of cover: ${levelOfCover}`;
        }

        if (budget) {
            string += ` with a ${frequency} budget of ${budget}`;
        }

        if (geography) {
            string += ` in the ${geography} geography`;
        }

        if (notes) {
            string += ` and has the following notes: ${notes}`;
        }
        setCustomerProfileString(string);
    };

    const handleSetFilter = (filter: FilterSettings) => {
        setFilterSettings(filter);
    };

    const handleSearchPromptTemplateChange = (e, newValue) => {
        setSearchPromptTemplate(newValue);
    };

    const onTempratureChange = (_ev, newValue) => {
        setTemprature(newValue);
    };

    const onSearchTempratureChange = (_ev, newValue) => {
        setSearchTemprature(newValue);
    };

    const onSearchTokensChange = (_ev, newValue) => {
        setSearchTokens(newValue);
    };

    const onSend = question => {
        makeApiRequest(question);
    };

    return (
        <div className={styles.container}>
            <div className={styles.commandsContainer}>
                <SearchFilterButton className={styles.commandButton} onClick={() => setIsFilterPanelOpen(!isFilterPanelOpen)} />
                <CustomerProfileButton className={styles.commandButton} onClick={() => setIsProfilePanelOpen(!isProfilePanelOpen)} />
                <SettingsButton className={styles.commandButton} onClick={() => setIsConfigPanelOpen(!isConfigPanelOpen)} />
                <ClearChatButton className={styles.commandButton} onClick={clearChat} disabled={!lastQuestionRef.current || isLoading} />
            </div>
            <div className={styles.chatRoot}>
                <Panel
                    headerText="Filter database search"
                    isOpen={isFilterPanelOpen}
                    isBlocking={false}
                    onDismiss={() => setIsFilterPanelOpen(false)}
                    closeButtonAriaLabel="Close"
                >
                    <FilterPanel
                        className={styles.profilePanel}
                        onSetFilter={handleSetFilter}
                        defaultQuery={searchPromptTemplate}
                        searchTemperature={searchTemprature}
                        onQueryPromptChange={handleSearchPromptTemplateChange}
                        onSearchTempratureChange={onSearchTempratureChange}
                        searchTokens={searchTokens}
                        onSearchTokensChange={onSearchTokensChange}
                    />
                </Panel>

                {/* Profile Panel */}

                <Panel
                    headerText="Configure customer profile"
                    isOpen={isProfilePanelOpen}
                    isBlocking={false}
                    onDismiss={() => setIsProfilePanelOpen(false)}
                    closeButtonAriaLabel="Close"
                >
                    <ProfilePanel className={styles.profilePanel} setProfile={setProfile} />
                </Panel>

                <div className={styles.chatContainer}>
                    {!lastQuestionRef.current ? (
                        <div className={styles.chatEmptyState}>
                            <img src={helper} alt="Chat logo" />
                            <h1 className={styles.chatEmptyStateTitle}>How can I help you today?</h1>
                            <h2 className={styles.chatEmptyStateSubtitle}>Ask me anything or try an example below</h2>
                            <ExampleList onExampleClicked={onExampleClicked} />
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
                        <QuestionInput
                            clearOnSend
                            placeholder="Type a new question (e.g. does my plan cover annual eye exams?)"
                            disabled={isLoading}
                            onSend={onSend}
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

                <Panel
                    headerText="Chat Settings"
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
                        label="Chat prompt"
                        multiline
                        rows={20}
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
                    <TextField className={styles.chatSettingsSeparator} label="Temprature" value={temprature} onChange={onTempratureChange} />
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
                </Panel>
            </div>
        </div>
    );
};

export default Chat;
