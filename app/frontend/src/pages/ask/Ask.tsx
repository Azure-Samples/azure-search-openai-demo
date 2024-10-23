import { useContext, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Helmet } from "react-helmet-async";
import {
    Checkbox,
    Panel,
    DefaultButton,
    Spinner,
    TextField,
    ICheckboxProps,
    ITextFieldProps,
    Dropdown,
    IDropdownOption,
    IDropdownProps
} from "@fluentui/react";
import { useId } from "@fluentui/react-hooks";

import styles from "./Ask.module.css";

import { askApi, configApi, ChatAppResponse, ChatAppRequest, RetrievalMode, VectorFieldOptions, GPT4VInput, SpeechConfig } from "../../api";
import { Answer, AnswerError } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";
import { HelpCallout } from "../../components/HelpCallout";
import { SettingsButton } from "../../components/SettingsButton/SettingsButton";
import { useLogin, getToken, requireAccessControl, checkLoggedIn } from "../../authConfig";
import { VectorSettings } from "../../components/VectorSettings";
import { GPT4VSettings } from "../../components/GPT4VSettings";
import { UploadFile } from "../../components/UploadFile";

import { useMsal } from "@azure/msal-react";
import { TokenClaimsDisplay } from "../../components/TokenClaimsDisplay";
import { LoginContext } from "../../loginContext";
import { LanguagePicker } from "../../i18n/LanguagePicker";

export function Component(): JSX.Element {
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
    const [promptTemplate, setPromptTemplate] = useState<string>("");
    const [promptTemplatePrefix, setPromptTemplatePrefix] = useState<string>("");
    const [promptTemplateSuffix, setPromptTemplateSuffix] = useState<string>("");
    const [temperature, setTemperature] = useState<number>(0.3);
    const [seed, setSeed] = useState<number | null>(null);
    const [minimumRerankerScore, setMinimumRerankerScore] = useState<number>(0);
    const [minimumSearchScore, setMinimumSearchScore] = useState<number>(0);
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    const [retrieveCount, setRetrieveCount] = useState<number>(3);
    const [useSemanticRanker, setUseSemanticRanker] = useState<boolean>(true);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);
    const [useGPT4V, setUseGPT4V] = useState<boolean>(false);
    const [gpt4vInput, setGPT4VInput] = useState<GPT4VInput>(GPT4VInput.TextAndImages);
    const [includeCategory, setIncludeCategory] = useState<string>("");
    const [excludeCategory, setExcludeCategory] = useState<string>("");
    const [question, setQuestion] = useState<string>("");
    const [vectorFieldList, setVectorFieldList] = useState<VectorFieldOptions[]>([VectorFieldOptions.Embedding, VectorFieldOptions.ImageEmbedding]);
    const [useOidSecurityFilter, setUseOidSecurityFilter] = useState<boolean>(false);
    const [useGroupsSecurityFilter, setUseGroupsSecurityFilter] = useState<boolean>(false);
    const [showGPT4VOptions, setShowGPT4VOptions] = useState<boolean>(false);
    const [showSemanticRankerOption, setShowSemanticRankerOption] = useState<boolean>(false);
    const [showVectorOption, setShowVectorOption] = useState<boolean>(false);
    const [showUserUpload, setShowUserUpload] = useState<boolean>(false);
    const [showLanguagePicker, setshowLanguagePicker] = useState<boolean>(false);
    const [showSpeechInput, setShowSpeechInput] = useState<boolean>(false);
    const [showSpeechOutputBrowser, setShowSpeechOutputBrowser] = useState<boolean>(false);
    const [showSpeechOutputAzure, setShowSpeechOutputAzure] = useState<boolean>(false);
    const audio = useRef(new Audio()).current;
    const [isPlaying, setIsPlaying] = useState(false);

    const lastQuestionRef = useRef<string>("");

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();
    const [answer, setAnswer] = useState<ChatAppResponse>();
    // For the Ask tab, this array will hold a maximum of one URL
    const [speechUrls, setSpeechUrls] = useState<(string | null)[]>([]);

    const speechConfig: SpeechConfig = {
        speechUrls,
        setSpeechUrls,
        audio,
        isPlaying,
        setIsPlaying
    };

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    const client = useLogin ? useMsal().instance : undefined;
    const { loggedIn } = useContext(LoginContext);

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
            setshowLanguagePicker(config.showLanguagePicker);
            setShowSpeechInput(config.showSpeechInput);
            setShowSpeechOutputBrowser(config.showSpeechOutputBrowser);
            setShowSpeechOutputAzure(config.showSpeechOutputAzure);
        });
    };

    useEffect(() => {
        getConfig();
    }, []);

    const makeApiRequest = async (question: string) => {
        lastQuestionRef.current = question;

        error && setError(undefined);
        setIsLoading(true);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);

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
                        include_category: includeCategory.length === 0 ? undefined : includeCategory,
                        exclude_category: excludeCategory.length === 0 ? undefined : excludeCategory,
                        top: retrieveCount,
                        temperature: temperature,
                        minimum_reranker_score: minimumRerankerScore,
                        minimum_search_score: minimumSearchScore,
                        retrieval_mode: retrievalMode,
                        semantic_ranker: useSemanticRanker,
                        semantic_captions: useSemanticCaptions,
                        use_oid_security_filter: useOidSecurityFilter,
                        use_groups_security_filter: useGroupsSecurityFilter,
                        vector_fields: vectorFieldList,
                        use_gpt4v: useGPT4V,
                        gpt4v_input: gpt4vInput,
                        language: i18n.language,
                        ...(seed !== null ? { seed: seed } : {})
                    }
                },
                // AI Chat Protocol: Client must pass on any session state received from the server
                session_state: answer ? answer.session_state : null
            };
            const result = await askApi(request, token);
            setAnswer(result);
            setSpeechUrls([null]);
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

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
        setMinimumSearchScore(parseFloat(newValue || "0"));
    };

    const onMinimumRerankerScoreChange = (_ev?: React.SyntheticEvent<HTMLElement, Event>, newValue?: string) => {
        setMinimumRerankerScore(parseFloat(newValue || "0"));
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

    const onIncludeCategoryChanged = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, option?: IDropdownOption) => {
        setIncludeCategory((option?.key as string) || "");
    };

    const onExcludeCategoryChanged = (_ev?: React.FormEvent, newValue?: string) => {
        setExcludeCategory(newValue || "");
    };

    const onExampleClicked = (example: string) => {
        makeApiRequest(example);
        setQuestion(example);
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
    const useOidSecurityFilterId = useId("useOidSecurityFilter");
    const useOidSecurityFilterFieldId = useId("useOidSecurityFilterField");
    const useGroupsSecurityFilterId = useId("useGroupsSecurityFilter");
    const useGroupsSecurityFilterFieldId = useId("useGroupsSecurityFilterField");
    const { t, i18n } = useTranslation();

    return (
        <div className={styles.askContainer}>
            {/* Setting the page title using react-helmet-async */}
            <Helmet>
                <title>{t("pageTitle")}</title>
            </Helmet>
            <div className={styles.askTopSection}>
                <div className={styles.commandsContainer}>
                    {showUserUpload && <UploadFile className={styles.commandButton} disabled={loggedIn} />}
                    <SettingsButton className={styles.commandButton} onClick={() => setIsConfigPanelOpen(!isConfigPanelOpen)} />
                </div>
                <h1 className={styles.askTitle}>{t("askTitle")}</h1>
                <div className={styles.askQuestionInput}>
                    <QuestionInput
                        placeholder={t("gpt4vExamples.placeholder")}
                        disabled={isLoading}
                        initQuestion={question}
                        onSend={question => makeApiRequest(question)}
                        showSpeechInput={showSpeechInput}
                    />
                </div>
            </div>
            <div className={styles.askBottomSection}>
                {isLoading && <Spinner label={t("generatingAnswer")} />}
                {!lastQuestionRef.current && (
                    <div className={styles.askTopSection}>
                        {showLanguagePicker && <LanguagePicker onLanguageChange={newLang => i18n.changeLanguage(newLang)} />}
                        <ExampleList onExampleClicked={onExampleClicked} useGPT4V={useGPT4V} />
                    </div>
                )}
                {!isLoading && answer && !error && (
                    <div className={styles.askAnswerContainer}>
                        <Answer
                            answer={answer}
                            index={0}
                            speechConfig={speechConfig}
                            isStreaming={false}
                            onCitationClicked={x => onShowCitation(x)}
                            onThoughtProcessClicked={() => onToggleTab(AnalysisPanelTabs.ThoughtProcessTab)}
                            onSupportingContentClicked={() => onToggleTab(AnalysisPanelTabs.SupportingContentTab)}
                            showSpeechOutputAzure={showSpeechOutputAzure}
                            showSpeechOutputBrowser={showSpeechOutputBrowser}
                        />
                    </div>
                )}
                {error ? (
                    <div className={styles.askAnswerContainer}>
                        <AnswerError error={error.toString()} onRetry={() => makeApiRequest(lastQuestionRef.current)} />
                    </div>
                ) : null}
                {activeAnalysisPanelTab && answer && (
                    <AnalysisPanel
                        className={styles.askAnalysisPanel}
                        activeCitation={activeCitation}
                        onActiveTabChanged={x => onToggleTab(x)}
                        citationHeight="600px"
                        answer={answer}
                        activeTab={activeAnalysisPanelTab}
                    />
                )}
            </div>

            <Panel
                headerText={t("labels.headerText")}
                isOpen={isConfigPanelOpen}
                isBlocking={false}
                onDismiss={() => setIsConfigPanelOpen(false)}
                closeButtonAriaLabel={t("labels.closeButton")}
                onRenderFooterContent={() => <DefaultButton onClick={() => setIsConfigPanelOpen(false)}>{t("labels.closeButton")}</DefaultButton>}
                isFooterAtBottom={true}
            >
                <TextField
                    id={promptTemplateFieldId}
                    className={styles.chatSettingsSeparator}
                    defaultValue={promptTemplate}
                    label={t("labels.promptTemplate")}
                    multiline
                    autoAdjustHeight
                    onChange={onPromptTemplateChange}
                    aria-labelledby={promptTemplateId}
                    onRenderLabel={(props: ITextFieldProps | undefined) => (
                        <HelpCallout labelId={promptTemplateId} fieldId={promptTemplateFieldId} helpText={t("helpTexts.promptTemplate")} label={props?.label} />
                    )}
                />

                <TextField
                    id={temperatureFieldId}
                    className={styles.chatSettingsSeparator}
                    label={t("labels.temperature")}
                    type="number"
                    min={0}
                    max={1}
                    step={0.1}
                    defaultValue={temperature.toString()}
                    onChange={onTemperatureChange}
                    aria-labelledby={temperatureId}
                    onRenderLabel={(props: ITextFieldProps | undefined) => (
                        <HelpCallout labelId={temperatureId} fieldId={temperatureFieldId} helpText={t("helpTexts.temperature")} label={props?.label} />
                    )}
                />

                <TextField
                    id={seedFieldId}
                    className={styles.chatSettingsSeparator}
                    label={t("labels.seed")}
                    type="text"
                    defaultValue={seed?.toString() || ""}
                    onChange={onSeedChange}
                    aria-labelledby={seedId}
                    onRenderLabel={(props: ITextFieldProps | undefined) => (
                        <HelpCallout labelId={seedId} fieldId={seedFieldId} helpText={t("helpTexts.seed")} label={props?.label} />
                    )}
                />

                <TextField
                    id={searchScoreFieldId}
                    className={styles.chatSettingsSeparator}
                    label={t("labels.minimumSearchScore")}
                    type="number"
                    min={0}
                    step={0.01}
                    defaultValue={minimumSearchScore.toString()}
                    onChange={onMinimumSearchScoreChange}
                    aria-labelledby={searchScoreId}
                    onRenderLabel={(props: ITextFieldProps | undefined) => (
                        <HelpCallout labelId={searchScoreId} fieldId={searchScoreFieldId} helpText={t("helpTexts.searchScore")} label={props?.label} />
                    )}
                />

                {showSemanticRankerOption && (
                    <TextField
                        id={rerankerScoreFieldId}
                        className={styles.chatSettingsSeparator}
                        label={t("labels.minimumRerankerScore")}
                        type="number"
                        min={1}
                        max={4}
                        step={0.1}
                        defaultValue={minimumRerankerScore.toString()}
                        onChange={onMinimumRerankerScoreChange}
                        aria-labelledby={rerankerScoreId}
                        onRenderLabel={(props: ITextFieldProps | undefined) => (
                            <HelpCallout
                                labelId={rerankerScoreId}
                                fieldId={rerankerScoreFieldId}
                                helpText={t("helpTexts.rerankerScore")}
                                label={props?.label}
                            />
                        )}
                    />
                )}

                <TextField
                    id={retrieveCountFieldId}
                    className={styles.chatSettingsSeparator}
                    label={t("labels.retrieveCount")}
                    type="number"
                    min={1}
                    max={50}
                    defaultValue={retrieveCount.toString()}
                    onChange={onRetrieveCountChange}
                    aria-labelledby={retrieveCountId}
                    onRenderLabel={(props: ITextFieldProps | undefined) => (
                        <HelpCallout labelId={retrieveCountId} fieldId={retrieveCountFieldId} helpText={t("helpTexts.retrieveNumber")} label={props?.label} />
                    )}
                />

                <Dropdown
                    id={includeCategoryFieldId}
                    className={styles.chatSettingsSeparator}
                    label={t("labels.includeCategory")}
                    selectedKey={includeCategory}
                    onChange={onIncludeCategoryChanged}
                    aria-labelledby={includeCategoryId}
                    options={[{ key: "", text: t("labels.includeCategoryOptions.all") }]}
                    onRenderLabel={(props: IDropdownProps | undefined) => (
                        <HelpCallout
                            labelId={includeCategoryId}
                            fieldId={includeCategoryFieldId}
                            helpText={t("helpTexts.includeCategory")}
                            label={props?.label}
                        />
                    )}
                />

                <TextField
                    id={excludeCategoryFieldId}
                    className={styles.chatSettingsSeparator}
                    label={t("labels.excludeCategory")}
                    defaultValue={excludeCategory}
                    onChange={onExcludeCategoryChanged}
                    aria-labelledby={excludeCategoryId}
                    onRenderLabel={(props: ITextFieldProps | undefined) => (
                        <HelpCallout
                            labelId={excludeCategoryId}
                            fieldId={excludeCategoryFieldId}
                            helpText={t("helpTexts.excludeCategory")}
                            label={props?.label}
                        />
                    )}
                />

                {showSemanticRankerOption && (
                    <>
                        <Checkbox
                            id={semanticRankerFieldId}
                            className={styles.chatSettingsSeparator}
                            checked={useSemanticRanker}
                            label={t("labels.useSemanticRanker")}
                            onChange={onUseSemanticRankerChange}
                            aria-labelledby={semanticRankerId}
                            onRenderLabel={(props: ICheckboxProps | undefined) => (
                                <HelpCallout
                                    labelId={semanticRankerId}
                                    fieldId={semanticRankerFieldId}
                                    helpText={t("helpTexts.useSemanticReranker")}
                                    label={props?.label}
                                />
                            )}
                        />

                        <Checkbox
                            id={semanticCaptionsFieldId}
                            className={styles.chatSettingsSeparator}
                            checked={useSemanticCaptions}
                            label={t("labels.useSemanticCaptions")}
                            onChange={onUseSemanticCaptionsChange}
                            disabled={!useSemanticRanker}
                            aria-labelledby={semanticCaptionsId}
                            onRenderLabel={(props: ICheckboxProps | undefined) => (
                                <HelpCallout
                                    labelId={semanticCaptionsId}
                                    fieldId={semanticCaptionsFieldId}
                                    helpText={t("helpTexts.useSemanticCaptions")}
                                    label={props?.label}
                                />
                            )}
                        />
                    </>
                )}

                {showGPT4VOptions && (
                    <GPT4VSettings
                        gpt4vInputs={gpt4vInput}
                        isUseGPT4V={useGPT4V}
                        updateUseGPT4V={useGPT4V => {
                            setUseGPT4V(useGPT4V);
                        }}
                        updateGPT4VInputs={inputs => setGPT4VInput(inputs)}
                    />
                )}

                {showVectorOption && (
                    <VectorSettings
                        defaultRetrievalMode={retrievalMode}
                        showImageOptions={useGPT4V && showGPT4VOptions}
                        updateVectorFields={(options: VectorFieldOptions[]) => setVectorFieldList(options)}
                        updateRetrievalMode={(retrievalMode: RetrievalMode) => setRetrievalMode(retrievalMode)}
                    />
                )}

                {useLogin && (
                    <>
                        <Checkbox
                            id={useOidSecurityFilterFieldId}
                            className={styles.chatSettingsSeparator}
                            checked={useOidSecurityFilter || requireAccessControl}
                            label={t("labels.useOidSecurityFilter")}
                            disabled={!loggedIn || requireAccessControl}
                            onChange={onUseOidSecurityFilterChange}
                            aria-labelledby={useOidSecurityFilterId}
                            onRenderLabel={(props: ICheckboxProps | undefined) => (
                                <HelpCallout
                                    labelId={useOidSecurityFilterId}
                                    fieldId={useOidSecurityFilterFieldId}
                                    helpText={t("helpTexts.useOidSecurityFilter")}
                                    label={props?.label}
                                />
                            )}
                        />
                        <Checkbox
                            id={useGroupsSecurityFilterFieldId}
                            className={styles.chatSettingsSeparator}
                            checked={useGroupsSecurityFilter || requireAccessControl}
                            label={t("labels.useGroupsSecurityFilter")}
                            disabled={!loggedIn || requireAccessControl}
                            onChange={onUseGroupsSecurityFilterChange}
                            aria-labelledby={useGroupsSecurityFilterId}
                            onRenderLabel={(props: ICheckboxProps | undefined) => (
                                <HelpCallout
                                    labelId={useGroupsSecurityFilterId}
                                    fieldId={useGroupsSecurityFilterFieldId}
                                    helpText={t("helpTexts.useGroupsSecurityFilter")}
                                    label={props?.label}
                                />
                            )}
                        />
                    </>
                )}
                {useLogin && <TokenClaimsDisplay />}
            </Panel>
        </div>
    );
}

Component.displayName = "Ask";
