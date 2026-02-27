import { useId } from "react";
import { useTranslation } from "react-i18next";
import { Input, Textarea, Checkbox, Dropdown, Option } from "@fluentui/react-components";
import type { OptionOnSelectData, SelectionEvents } from "@fluentui/react-components";
import { HelpCallout } from "../HelpCallout";
import { VectorSettings } from "../VectorSettings";
import { RetrievalMode } from "../../api";
import styles from "./Settings.module.css";

export interface SettingsProps {
    promptTemplate: string;
    temperature: number;
    retrieveCount: number;
    agenticReasoningEffort: string;
    seed: number | null;
    minimumSearchScore: number;
    minimumRerankerScore: number;
    useSemanticRanker: boolean;
    useSemanticCaptions: boolean;
    useQueryRewriting: boolean;
    reasoningEffort: string;
    excludeCategory: string;
    includeCategory: string;
    retrievalMode: RetrievalMode;
    sendTextSources: boolean;
    sendImageSources: boolean;
    searchTextEmbeddings: boolean;
    searchImageEmbeddings: boolean;
    showSemanticRankerOption: boolean;
    showQueryRewritingOption: boolean;
    showReasoningEffortOption: boolean;
    showMultimodalOptions: boolean;
    showVectorOption: boolean;
    useLogin: boolean;
    loggedIn: boolean;
    requireAccessControl: boolean;
    className?: string;
    onChange: (field: string, value: any) => void;
    streamingEnabled?: boolean; // Only used in chat
    shouldStream?: boolean; // Only used in Chat
    useSuggestFollowupQuestions?: boolean; // Only used in Chat
    promptTemplatePrefix?: string;
    promptTemplateSuffix?: string;
    showAgenticRetrievalOption?: boolean;
    useAgenticKnowledgeBase?: boolean;
    hideMinimalRetrievalReasoningOption?: boolean;
    useWebSource?: boolean;
    showWebSourceOption?: boolean;
    useSharePointSource?: boolean;
    showSharePointSourceOption?: boolean;
}

export const Settings = ({
    promptTemplate,
    temperature,
    retrieveCount,
    agenticReasoningEffort,
    seed,
    minimumSearchScore,
    minimumRerankerScore,
    useSemanticRanker,
    useSemanticCaptions,
    useQueryRewriting,
    reasoningEffort,
    excludeCategory,
    includeCategory,
    retrievalMode,
    searchTextEmbeddings,
    searchImageEmbeddings,
    sendTextSources,
    sendImageSources,
    showSemanticRankerOption,
    showQueryRewritingOption,
    showReasoningEffortOption,
    showMultimodalOptions,
    showVectorOption,
    useLogin,
    loggedIn,
    requireAccessControl,
    className,
    onChange,
    streamingEnabled,
    shouldStream,
    useSuggestFollowupQuestions,
    promptTemplatePrefix,
    promptTemplateSuffix,
    showAgenticRetrievalOption,
    useAgenticKnowledgeBase = false,
    hideMinimalRetrievalReasoningOption = false,
    useWebSource = false,
    showWebSourceOption = false,
    useSharePointSource = false,
    showSharePointSourceOption = false
}: SettingsProps) => {
    const { t } = useTranslation();

    // Form field IDs
    const promptTemplateId = useId();
    const promptTemplateFieldId = useId();
    const temperatureId = useId();
    const temperatureFieldId = useId();
    const seedId = useId();
    const seedFieldId = useId();
    const agenticRetrievalId = useId();
    const agenticRetrievalFieldId = useId();
    const webSourceId = useId();
    const webSourceFieldId = useId();
    const sharePointSourceId = useId();
    const sharePointSourceFieldId = useId();
    const searchScoreId = useId();
    const searchScoreFieldId = useId();
    const rerankerScoreId = useId();
    const rerankerScoreFieldId = useId();
    const retrieveCountId = useId();
    const retrieveCountFieldId = useId();
    const agenticReasoningEffortId = useId();
    const agenticReasoningEffortFieldId = useId();
    const includeCategoryId = useId();
    const includeCategoryFieldId = useId();
    const excludeCategoryId = useId();
    const excludeCategoryFieldId = useId();
    const semanticRankerId = useId();
    const semanticRankerFieldId = useId();
    const queryRewritingId = useId();
    const queryRewritingFieldId = useId();
    const reasoningEffortId = useId();
    const reasoningEffortFieldId = useId();
    const semanticCaptionsId = useId();
    const semanticCaptionsFieldId = useId();
    const shouldStreamId = useId();
    const shouldStreamFieldId = useId();
    const suggestFollowupQuestionsId = useId();
    const suggestFollowupQuestionsFieldId = useId();

    const webSourceDisablesStreamingAndFollowup = !!useWebSource;

    const retrievalReasoningOptions: { key: string; text: string }[] = [
        { key: "minimal", text: t("labels.agenticReasoningEffortOptions.minimal") },
        { key: "low", text: t("labels.agenticReasoningEffortOptions.low") },
        { key: "medium", text: t("labels.agenticReasoningEffortOptions.medium") }
    ];

    return (
        <div className={className}>
            {streamingEnabled && (
                <>
                    <div className={styles.settingsCheckbox}>
                        <Checkbox
                            id={shouldStreamFieldId}
                            checked={webSourceDisablesStreamingAndFollowup ? false : shouldStream}
                            onChange={(_ev, data) => onChange("shouldStream", !!data.checked)}
                            aria-labelledby={shouldStreamId}
                            disabled={webSourceDisablesStreamingAndFollowup}
                        />
                        <HelpCallout
                            labelId={shouldStreamId}
                            fieldId={shouldStreamFieldId}
                            helpText={t("helpTexts.streamChat")}
                            label={t("labels.shouldStream")}
                        />
                    </div>

                    <div className={styles.settingsCheckbox}>
                        <Checkbox
                            id={suggestFollowupQuestionsFieldId}
                            checked={webSourceDisablesStreamingAndFollowup ? false : useSuggestFollowupQuestions}
                            onChange={(_ev, data) => onChange("useSuggestFollowupQuestions", !!data.checked)}
                            aria-labelledby={suggestFollowupQuestionsId}
                            disabled={webSourceDisablesStreamingAndFollowup}
                        />
                        <HelpCallout
                            labelId={suggestFollowupQuestionsId}
                            fieldId={suggestFollowupQuestionsFieldId}
                            helpText={t("helpTexts.suggestFollowupQuestions")}
                            label={t("labels.useSuggestFollowupQuestions")}
                        />
                    </div>
                </>
            )}

            <h3 className={styles.sectionHeader}>{t("searchSettings")}</h3>

            {showAgenticRetrievalOption && (
                <>
                    <div className={styles.settingsCheckbox}>
                        <Checkbox
                            id={agenticRetrievalFieldId}
                            checked={useAgenticKnowledgeBase}
                            onChange={(_ev, data) => onChange("useAgenticKnowledgeBase", !!data.checked)}
                            aria-labelledby={agenticRetrievalId}
                        />
                        <HelpCallout
                            labelId={agenticRetrievalId}
                            fieldId={agenticRetrievalFieldId}
                            helpText={t("helpTexts.useAgenticKnowledgeBase")}
                            label={t("labels.useAgenticKnowledgeBase")}
                        />
                    </div>
                </>
            )}

            {showAgenticRetrievalOption && useAgenticKnowledgeBase && (
                <>
                    <div className={styles.settingsField}>
                        <HelpCallout
                            labelId={agenticReasoningEffortId}
                            fieldId={agenticReasoningEffortFieldId}
                            helpText={t("helpTexts.agenticReasoningEffort")}
                            label={t("labels.agenticReasoningEffort")}
                        />
                        <Dropdown
                            id={agenticReasoningEffortFieldId}
                            selectedOptions={[agenticReasoningEffort]}
                            value={retrievalReasoningOptions.find(o => o.key === agenticReasoningEffort)?.text || agenticReasoningEffort}
                            onOptionSelect={(_ev: SelectionEvents, data: OptionOnSelectData) => {
                                const newValue = data.optionValue ?? agenticReasoningEffort;
                                onChange("agenticReasoningEffort", newValue);
                                if (newValue === "minimal" && useWebSource) {
                                    onChange("useWebSource", false);
                                }
                            }}
                            aria-labelledby={agenticReasoningEffortId}
                        >
                            {retrievalReasoningOptions.map(opt => (
                                <Option key={opt.key} value={opt.key}>
                                    {opt.text}
                                </Option>
                            ))}
                        </Dropdown>
                    </div>
                </>
            )}

            {showAgenticRetrievalOption && useAgenticKnowledgeBase && showWebSourceOption && (
                <>
                    <div className={styles.settingsCheckbox}>
                        <Checkbox
                            id={webSourceFieldId}
                            checked={useWebSource}
                            onChange={(_ev, data) => {
                                onChange("useWebSource", !!data.checked);
                                if (data.checked) {
                                    if (shouldStream) {
                                        onChange("shouldStream", false);
                                    }
                                    if (useSuggestFollowupQuestions) {
                                        onChange("useSuggestFollowupQuestions", false);
                                    }
                                }
                            }}
                            aria-labelledby={webSourceId}
                            disabled={!useAgenticKnowledgeBase || agenticReasoningEffort === "minimal"}
                        />
                        <HelpCallout labelId={webSourceId} fieldId={webSourceFieldId} helpText={t("helpTexts.useWebSource")} label={t("labels.useWebSource")} />
                    </div>
                </>
            )}
            {showAgenticRetrievalOption && useAgenticKnowledgeBase && showSharePointSourceOption && (
                <>
                    <div className={styles.settingsCheckbox}>
                        <Checkbox
                            id={sharePointSourceFieldId}
                            checked={useSharePointSource}
                            onChange={(_ev, data) => onChange("useSharePointSource", !!data.checked)}
                            aria-labelledby={sharePointSourceId}
                            disabled={!useAgenticKnowledgeBase}
                        />
                        <HelpCallout
                            labelId={sharePointSourceId}
                            fieldId={sharePointSourceFieldId}
                            helpText={t("helpTexts.useSharePointSource")}
                            label={t("labels.useSharePointSource")}
                        />
                    </div>
                </>
            )}
            {!useAgenticKnowledgeBase && (
                <>
                    <div className={styles.settingsField}>
                        <HelpCallout
                            labelId={searchScoreId}
                            fieldId={searchScoreFieldId}
                            helpText={t("helpTexts.searchScore")}
                            label={t("labels.minimumSearchScore")}
                        />
                        <Input
                            id={searchScoreFieldId}
                            type="number"
                            min={0}
                            step={0.01}
                            defaultValue={minimumSearchScore.toString()}
                            onChange={(_ev, data) => onChange("minimumSearchScore", parseFloat(data.value || "0"))}
                            aria-labelledby={searchScoreId}
                        />
                    </div>
                </>
            )}

            {showSemanticRankerOption && (
                <>
                    <div className={styles.settingsField}>
                        <HelpCallout
                            labelId={rerankerScoreId}
                            fieldId={rerankerScoreFieldId}
                            helpText={t("helpTexts.rerankerScore")}
                            label={t("labels.minimumRerankerScore")}
                        />
                        <Input
                            id={rerankerScoreFieldId}
                            type="number"
                            min={1}
                            max={4}
                            step={0.1}
                            defaultValue={minimumRerankerScore.toString()}
                            onChange={(_ev, data) => onChange("minimumRerankerScore", parseFloat(data.value || "0"))}
                            aria-labelledby={rerankerScoreId}
                        />
                    </div>
                </>
            )}

            {!useAgenticKnowledgeBase && (
                <>
                    <div className={styles.settingsField}>
                        <HelpCallout
                            labelId={retrieveCountId}
                            fieldId={retrieveCountFieldId}
                            helpText={t("helpTexts.retrieveNumber")}
                            label={t("labels.retrieveCount")}
                        />
                        <Input
                            id={retrieveCountFieldId}
                            type="number"
                            min={1}
                            max={50}
                            defaultValue={retrieveCount.toString()}
                            onChange={(_ev, data) => onChange("retrieveCount", parseInt(data.value || "3"))}
                            aria-labelledby={retrieveCountId}
                        />
                    </div>
                </>
            )}
            <div className={styles.settingsField}>
                <HelpCallout
                    labelId={includeCategoryId}
                    fieldId={includeCategoryFieldId}
                    helpText={t("helpTexts.includeCategory")}
                    label={t("labels.includeCategory")}
                />
                <Dropdown
                    id={includeCategoryFieldId}
                    selectedOptions={[includeCategory]}
                    value={includeCategory === "" ? t("labels.includeCategoryOptions.all") : includeCategory}
                    onOptionSelect={(_ev: SelectionEvents, data: OptionOnSelectData) => onChange("includeCategory", data.optionValue || "")}
                    aria-labelledby={includeCategoryId}
                >
                    <Option value="">{t("labels.includeCategoryOptions.all")}</Option>
                </Dropdown>
            </div>
            <div className={styles.settingsField}>
                <HelpCallout
                    labelId={excludeCategoryId}
                    fieldId={excludeCategoryFieldId}
                    helpText={t("helpTexts.excludeCategory")}
                    label={t("labels.excludeCategory")}
                />
                <Input
                    id={excludeCategoryFieldId}
                    defaultValue={excludeCategory}
                    onChange={(_ev, data) => onChange("excludeCategory", data.value || "")}
                    aria-labelledby={excludeCategoryId}
                />
            </div>
            {showSemanticRankerOption && !useAgenticKnowledgeBase && (
                <>
                    <div className={styles.settingsCheckbox}>
                        <Checkbox
                            id={semanticRankerFieldId}
                            checked={useSemanticRanker}
                            onChange={(_ev, data) => onChange("useSemanticRanker", !!data.checked)}
                            aria-labelledby={semanticRankerId}
                        />
                        <HelpCallout
                            labelId={semanticRankerId}
                            fieldId={semanticRankerFieldId}
                            helpText={t("helpTexts.useSemanticReranker")}
                            label={t("labels.useSemanticRanker")}
                        />
                    </div>

                    <div className={styles.settingsCheckbox}>
                        <Checkbox
                            id={semanticCaptionsFieldId}
                            checked={useSemanticCaptions}
                            onChange={(_ev, data) => onChange("useSemanticCaptions", !!data.checked)}
                            disabled={!useSemanticRanker}
                            aria-labelledby={semanticCaptionsId}
                        />
                        <HelpCallout
                            labelId={semanticCaptionsId}
                            fieldId={semanticCaptionsFieldId}
                            helpText={t("helpTexts.useSemanticCaptions")}
                            label={t("labels.useSemanticCaptions")}
                        />
                    </div>
                </>
            )}
            {showQueryRewritingOption && !useAgenticKnowledgeBase && (
                <>
                    <div className={styles.settingsCheckbox}>
                        <Checkbox
                            id={queryRewritingFieldId}
                            checked={useQueryRewriting}
                            disabled={!useSemanticRanker}
                            onChange={(_ev, data) => onChange("useQueryRewriting", !!data.checked)}
                            aria-labelledby={queryRewritingId}
                        />
                        <HelpCallout
                            labelId={queryRewritingId}
                            fieldId={queryRewritingFieldId}
                            helpText={t("helpTexts.useQueryRewriting")}
                            label={t("labels.useQueryRewriting")}
                        />
                    </div>
                </>
            )}
            {showReasoningEffortOption && (
                <>
                    <div className={styles.settingsField}>
                        <HelpCallout
                            labelId={reasoningEffortId}
                            fieldId={reasoningEffortFieldId}
                            helpText={t("helpTexts.reasoningEffort")}
                            label={t("labels.reasoningEffort")}
                        />
                        <Dropdown
                            id={reasoningEffortFieldId}
                            selectedOptions={[reasoningEffort]}
                            value={
                                reasoningEffort === "minimal"
                                    ? t("labels.reasoningEffortOptions.minimal")
                                    : reasoningEffort === "low"
                                      ? t("labels.reasoningEffortOptions.low")
                                      : reasoningEffort === "medium"
                                        ? t("labels.reasoningEffortOptions.medium")
                                        : t("labels.reasoningEffortOptions.high")
                            }
                            onOptionSelect={(_ev: SelectionEvents, data: OptionOnSelectData) => onChange("reasoningEffort", data.optionValue || "")}
                            aria-labelledby={reasoningEffortId}
                        >
                            <Option value="minimal">{t("labels.reasoningEffortOptions.minimal")}</Option>
                            <Option value="low">{t("labels.reasoningEffortOptions.low")}</Option>
                            <Option value="medium">{t("labels.reasoningEffortOptions.medium")}</Option>
                            <Option value="high">{t("labels.reasoningEffortOptions.high")}</Option>
                        </Dropdown>
                    </div>
                </>
            )}
            {showVectorOption && !useAgenticKnowledgeBase && (
                <>
                    <VectorSettings
                        defaultRetrievalMode={retrievalMode}
                        defaultSearchTextEmbeddings={searchTextEmbeddings}
                        defaultSearchImageEmbeddings={searchImageEmbeddings}
                        showImageOptions={showMultimodalOptions}
                        updateRetrievalMode={val => onChange("retrievalMode", val)}
                        updateSearchTextEmbeddings={val => onChange("searchTextEmbeddings", val)}
                        updateSearchImageEmbeddings={val => onChange("searchImageEmbeddings", val)}
                    />
                </>
            )}

            {!useWebSource && (
                <>
                    <h3 className={styles.sectionHeader}>{t("llmSettings")}</h3>
                    <div className={styles.settingsField}>
                        <HelpCallout
                            labelId={promptTemplateId}
                            fieldId={promptTemplateFieldId}
                            helpText={t("helpTexts.promptTemplate")}
                            label={t("labels.promptTemplate")}
                        />
                        <Textarea
                            id={promptTemplateFieldId}
                            defaultValue={promptTemplate}
                            resize="vertical"
                            onChange={(_ev, data) => onChange("promptTemplate", data.value || "")}
                            aria-labelledby={promptTemplateId}
                        />
                    </div>
                    <div className={styles.settingsField}>
                        <HelpCallout
                            labelId={temperatureId}
                            fieldId={temperatureFieldId}
                            helpText={t("helpTexts.temperature")}
                            label={t("labels.temperature")}
                        />
                        <Input
                            id={temperatureFieldId}
                            type="number"
                            min={0}
                            max={1}
                            step={0.1}
                            defaultValue={temperature.toString()}
                            onChange={(_ev, data) => onChange("temperature", parseFloat(data.value || "0"))}
                            aria-labelledby={temperatureId}
                        />
                    </div>
                    <div className={styles.settingsField}>
                        <HelpCallout labelId={seedId} fieldId={seedFieldId} helpText={t("helpTexts.seed")} label={t("labels.seed")} />
                        <Input
                            id={seedFieldId}
                            type="text"
                            defaultValue={seed?.toString() || ""}
                            onChange={(_ev, data) => onChange("seed", data.value ? parseInt(data.value) : null)}
                            aria-labelledby={seedId}
                        />
                    </div>

                    {showMultimodalOptions && !useAgenticKnowledgeBase && (
                        <fieldset className={styles.fieldset + " " + styles.settingsField}>
                            <legend className={styles.legend}>{t("labels.llmInputs")}</legend>
                            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                                <div className={styles.settingsCheckbox} style={{ marginTop: 0 }}>
                                    <Checkbox
                                        id="sendTextSources"
                                        checked={sendTextSources}
                                        onChange={(_ev, data) => {
                                            onChange("sendTextSources", !!data.checked);
                                        }}
                                    />
                                    <HelpCallout
                                        labelId="sendTextSourcesLabel"
                                        fieldId="sendTextSources"
                                        helpText={t("helpTexts.llmTextInputs")}
                                        label={t("labels.llmInputsOptions.texts")}
                                    />
                                </div>
                                <div className={styles.settingsCheckbox} style={{ marginTop: 0 }}>
                                    <Checkbox
                                        id="sendImageSources"
                                        checked={sendImageSources}
                                        onChange={(_ev, data) => {
                                            onChange("sendImageSources", !!data.checked);
                                        }}
                                    />
                                    <HelpCallout
                                        labelId="sendImageSourcesLabel"
                                        fieldId="sendImageSources"
                                        helpText={t("helpTexts.llmImageInputs")}
                                        label={t("labels.llmInputsOptions.images")}
                                    />
                                </div>
                            </div>
                        </fieldset>
                    )}
                </>
            )}
        </div>
    );
};
