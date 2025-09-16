import { useId } from "@fluentui/react-hooks";
import { useTranslation } from "react-i18next";
import { TextField, ITextFieldProps, Checkbox, ICheckboxProps, Dropdown, IDropdownProps, IDropdownOption, Stack } from "@fluentui/react";
import { HelpCallout } from "../HelpCallout";
import { VectorSettings } from "../VectorSettings";
import { RetrievalMode } from "../../api";
import styles from "./Settings.module.css";

// Add type for onRenderLabel
type RenderLabelType = ITextFieldProps | IDropdownProps | ICheckboxProps;

export interface SettingsProps {
    promptTemplate: string;
    temperature: number;
    retrieveCount: number;
    resultsMergeStrategy: string;
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
    useOidSecurityFilter: boolean;
    useGroupsSecurityFilter: boolean;
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
    showSuggestFollowupQuestions?: boolean;
    showAgenticRetrievalOption: boolean;
    useAgenticRetrieval: boolean;
}

export const Settings = ({
    promptTemplate,
    temperature,
    retrieveCount,
    resultsMergeStrategy,
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
    useOidSecurityFilter,
    useGroupsSecurityFilter,
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
    showSuggestFollowupQuestions,
    showAgenticRetrievalOption,
    useAgenticRetrieval
}: SettingsProps) => {
    const { t } = useTranslation();

    // Form field IDs
    const promptTemplateId = useId("promptTemplate");
    const promptTemplateFieldId = useId("promptTemplateField");
    const temperatureId = useId("temperature");
    const temperatureFieldId = useId("temperatureField");
    const seedId = useId("seed");
    const seedFieldId = useId("seedField");
    const agenticRetrievalId = useId("agenticRetrieval");
    const agenticRetrievalFieldId = useId("agenticRetrievalField");
    const searchScoreId = useId("searchScore");
    const searchScoreFieldId = useId("searchScoreField");
    const rerankerScoreId = useId("rerankerScore");
    const rerankerScoreFieldId = useId("rerankerScoreField");
    const retrieveCountId = useId("retrieveCount");
    const retrieveCountFieldId = useId("retrieveCountField");
    const resultsMergeStrategyFieldId = useId("resultsMergeStrategy");
    const includeCategoryId = useId("includeCategory");
    const includeCategoryFieldId = useId("includeCategoryField");
    const excludeCategoryId = useId("excludeCategory");
    const excludeCategoryFieldId = useId("excludeCategoryField");
    const semanticRankerId = useId("semanticRanker");
    const semanticRankerFieldId = useId("semanticRankerField");
    const queryRewritingFieldId = useId("queryRewritingField");
    const reasoningEffortFieldId = useId("reasoningEffortField");
    const semanticCaptionsId = useId("semanticCaptions");
    const semanticCaptionsFieldId = useId("semanticCaptionsField");
    const useOidSecurityFilterId = useId("useOidSecurityFilter");
    const useOidSecurityFilterFieldId = useId("useOidSecurityFilterField");
    const useGroupsSecurityFilterId = useId("useGroupsSecurityFilter");
    const useGroupsSecurityFilterFieldId = useId("useGroupsSecurityFilterField");
    const shouldStreamId = useId("shouldStream");
    const shouldStreamFieldId = useId("shouldStreamField");
    const suggestFollowupQuestionsId = useId("suggestFollowupQuestions");
    const suggestFollowupQuestionsFieldId = useId("suggestFollowupQuestionsField");

    const renderLabel = (props: RenderLabelType | undefined, labelId: string, fieldId: string, helpText: string) => (
        <HelpCallout labelId={labelId} fieldId={fieldId} helpText={helpText} label={props?.label} />
    );

    return (
        <div className={className}>
            <h3 className={styles.sectionHeader}>{t("overallSettings")}</h3>

            {shouldStream !== undefined && (
                <Checkbox
                    id={shouldStreamFieldId}
                    disabled={!streamingEnabled}
                    className={styles.settingsSeparator}
                    checked={shouldStream}
                    label={t("labels.shouldStream")}
                    onChange={(_ev, checked) => onChange("shouldStream", !!checked)}
                    aria-labelledby={shouldStreamId}
                    onRenderLabel={props => renderLabel(props, shouldStreamId, shouldStreamFieldId, t("helpTexts.streamChat"))}
                />
            )}

            {showSuggestFollowupQuestions && (
                <Checkbox
                    id={suggestFollowupQuestionsFieldId}
                    className={styles.settingsSeparator}
                    checked={useSuggestFollowupQuestions}
                    label={t("labels.useSuggestFollowupQuestions")}
                    onChange={(_ev, checked) => onChange("useSuggestFollowupQuestions", !!checked)}
                    aria-labelledby={suggestFollowupQuestionsId}
                    onRenderLabel={props =>
                        renderLabel(props, suggestFollowupQuestionsId, suggestFollowupQuestionsFieldId, t("helpTexts.suggestFollowupQuestions"))
                    }
                />
            )}

            <h3 className={styles.sectionHeader}>{t("searchSettings")}</h3>

            {showAgenticRetrievalOption && (
                <Checkbox
                    id={agenticRetrievalFieldId}
                    className={styles.settingsSeparator}
                    checked={useAgenticRetrieval}
                    label={t("labels.useAgenticRetrieval")}
                    onChange={(_ev, checked) => onChange("useAgenticRetrieval", !!checked)}
                    aria-labelledby={agenticRetrievalId}
                    onRenderLabel={props => renderLabel(props, agenticRetrievalId, agenticRetrievalFieldId, t("helpTexts.useAgenticRetrieval"))}
                />
            )}
            {!useAgenticRetrieval && (
                <TextField
                    id={searchScoreFieldId}
                    className={styles.settingsSeparator}
                    label={t("labels.minimumSearchScore")}
                    type="number"
                    min={0}
                    step={0.01}
                    defaultValue={minimumSearchScore.toString()}
                    onChange={(_ev, val) => onChange("minimumSearchScore", parseFloat(val || "0"))}
                    aria-labelledby={searchScoreId}
                    onRenderLabel={props => renderLabel(props, searchScoreId, searchScoreFieldId, t("helpTexts.searchScore"))}
                />
            )}

            {showSemanticRankerOption && (
                <TextField
                    id={rerankerScoreFieldId}
                    className={styles.settingsSeparator}
                    label={t("labels.minimumRerankerScore")}
                    type="number"
                    min={1}
                    max={4}
                    step={0.1}
                    defaultValue={minimumRerankerScore.toString()}
                    onChange={(_ev, val) => onChange("minimumRerankerScore", parseFloat(val || "0"))}
                    aria-labelledby={rerankerScoreId}
                    onRenderLabel={props => renderLabel(props, rerankerScoreId, rerankerScoreFieldId, t("helpTexts.rerankerScore"))}
                />
            )}
            {showAgenticRetrievalOption && useAgenticRetrieval && (
                <Dropdown
                    id={resultsMergeStrategyFieldId}
                    className={styles.settingsSeparator}
                    label={t("labels.resultsMergeStrategy")}
                    selectedKey={resultsMergeStrategy}
                    onChange={(_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, option?: IDropdownOption) =>
                        onChange("resultsMergeStrategy", option?.key)
                    }
                    aria-labelledby={includeCategoryId}
                    options={[
                        { key: "interleaved", text: t("labels.resultsMergeStrategyOptions.interleaved") },
                        { key: "descending", text: t("labels.resultsMergeStrategyOptions.descending") }
                    ]}
                    onRenderLabel={props => renderLabel(props, includeCategoryId, includeCategoryFieldId, t("helpTexts.resultsMergeStrategy"))}
                />
            )}
            <TextField
                id={retrieveCountFieldId}
                className={styles.settingsSeparator}
                label={t("labels.retrieveCount")}
                type="number"
                min={1}
                max={50}
                defaultValue={retrieveCount.toString()}
                onChange={(_ev, val) => onChange("retrieveCount", parseInt(val || "3"))}
                aria-labelledby={retrieveCountId}
                onRenderLabel={props => renderLabel(props, retrieveCountId, retrieveCountFieldId, t("helpTexts.retrieveNumber"))}
            />
            <Dropdown
                id={includeCategoryFieldId}
                className={styles.settingsSeparator}
                label={t("labels.includeCategory")}
                selectedKey={includeCategory}
                onChange={(_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, option?: IDropdownOption) => onChange("includeCategory", option?.key || "")}
                aria-labelledby={includeCategoryId}
                options={[
                    { key: "", text: t("labels.includeCategoryOptions.all") }
                    // { key: "example", text: "Example Category" } // Add more categories as needed
                ]}
                onRenderLabel={props => renderLabel(props, includeCategoryId, includeCategoryFieldId, t("helpTexts.includeCategory"))}
            />
            <TextField
                id={excludeCategoryFieldId}
                className={styles.settingsSeparator}
                label={t("labels.excludeCategory")}
                defaultValue={excludeCategory}
                onChange={(_ev, val) => onChange("excludeCategory", val || "")}
                aria-labelledby={excludeCategoryId}
                onRenderLabel={props => renderLabel(props, excludeCategoryId, excludeCategoryFieldId, t("helpTexts.excludeCategory"))}
            />
            {showSemanticRankerOption && !useAgenticRetrieval && (
                <>
                    <Checkbox
                        id={semanticRankerFieldId}
                        className={styles.settingsSeparator}
                        checked={useSemanticRanker}
                        label={t("labels.useSemanticRanker")}
                        onChange={(_ev, checked) => onChange("useSemanticRanker", !!checked)}
                        aria-labelledby={semanticRankerId}
                        onRenderLabel={props => renderLabel(props, semanticRankerId, semanticRankerFieldId, t("helpTexts.useSemanticReranker"))}
                    />

                    <Checkbox
                        id={semanticCaptionsFieldId}
                        className={styles.settingsSeparator}
                        checked={useSemanticCaptions}
                        label={t("labels.useSemanticCaptions")}
                        onChange={(_ev, checked) => onChange("useSemanticCaptions", !!checked)}
                        disabled={!useSemanticRanker}
                        aria-labelledby={semanticCaptionsId}
                        onRenderLabel={props => renderLabel(props, semanticCaptionsId, semanticCaptionsFieldId, t("helpTexts.useSemanticCaptions"))}
                    />
                </>
            )}
            {showQueryRewritingOption && !useAgenticRetrieval && (
                <>
                    <Checkbox
                        id={queryRewritingFieldId}
                        className={styles.settingsSeparator}
                        checked={useQueryRewriting}
                        disabled={!useSemanticRanker}
                        label={t("labels.useQueryRewriting")}
                        onChange={(_ev, checked) => onChange("useQueryRewriting", !!checked)}
                        aria-labelledby={queryRewritingFieldId}
                        onRenderLabel={props => renderLabel(props, queryRewritingFieldId, queryRewritingFieldId, t("helpTexts.useQueryRewriting"))}
                    />
                </>
            )}
            {showReasoningEffortOption && (
                <Dropdown
                    id={reasoningEffortFieldId}
                    selectedKey={reasoningEffort}
                    label={t("labels.reasoningEffort")}
                    onChange={(_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, option?: IDropdownOption) =>
                        onChange("reasoningEffort", option?.key || "")
                    }
                    aria-labelledby={reasoningEffortFieldId}
                    options={[
                        { key: "minimal", text: t("labels.reasoningEffortOptions.minimal") },
                        { key: "low", text: t("labels.reasoningEffortOptions.low") },
                        { key: "medium", text: t("labels.reasoningEffortOptions.medium") },
                        { key: "high", text: t("labels.reasoningEffortOptions.high") }
                    ]}
                    onRenderLabel={props => renderLabel(props, queryRewritingFieldId, queryRewritingFieldId, t("helpTexts.reasoningEffort"))}
                />
            )}
            {useLogin && (
                <>
                    <Checkbox
                        id={useOidSecurityFilterFieldId}
                        className={styles.settingsSeparator}
                        checked={useOidSecurityFilter || requireAccessControl}
                        label={t("labels.useOidSecurityFilter")}
                        disabled={!loggedIn || requireAccessControl}
                        onChange={(_ev, checked) => onChange("useOidSecurityFilter", !!checked)}
                        aria-labelledby={useOidSecurityFilterId}
                        onRenderLabel={props => renderLabel(props, useOidSecurityFilterId, useOidSecurityFilterFieldId, t("helpTexts.useOidSecurityFilter"))}
                    />
                    <Checkbox
                        id={useGroupsSecurityFilterFieldId}
                        className={styles.settingsSeparator}
                        checked={useGroupsSecurityFilter || requireAccessControl}
                        label={t("labels.useGroupsSecurityFilter")}
                        disabled={!loggedIn || requireAccessControl}
                        onChange={(_ev, checked) => onChange("useGroupsSecurityFilter", !!checked)}
                        aria-labelledby={useGroupsSecurityFilterId}
                        onRenderLabel={props =>
                            renderLabel(props, useGroupsSecurityFilterId, useGroupsSecurityFilterFieldId, t("helpTexts.useGroupsSecurityFilter"))
                        }
                    />
                </>
            )}
            {showVectorOption && !useAgenticRetrieval && (
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

            <h3 className={styles.sectionHeader}>{t("llmSettings")}</h3>
            <TextField
                id={promptTemplateFieldId}
                className={styles.settingsSeparator}
                defaultValue={promptTemplate}
                label={t("labels.promptTemplate")}
                multiline
                autoAdjustHeight
                onChange={(_ev, val) => onChange("promptTemplate", val || "")}
                aria-labelledby={promptTemplateId}
                onRenderLabel={props => renderLabel(props, promptTemplateId, promptTemplateFieldId, t("helpTexts.promptTemplate"))}
            />
            <TextField
                id={temperatureFieldId}
                className={styles.settingsSeparator}
                label={t("labels.temperature")}
                type="number"
                min={0}
                max={1}
                step={0.1}
                defaultValue={temperature.toString()}
                onChange={(_ev, val) => onChange("temperature", parseFloat(val || "0"))}
                aria-labelledby={temperatureId}
                onRenderLabel={props => renderLabel(props, temperatureId, temperatureFieldId, t("helpTexts.temperature"))}
            />
            <TextField
                id={seedFieldId}
                className={styles.settingsSeparator}
                label={t("labels.seed")}
                type="text"
                defaultValue={seed?.toString() || ""}
                onChange={(_ev, val) => onChange("seed", val ? parseInt(val) : null)}
                aria-labelledby={seedId}
                onRenderLabel={props => renderLabel(props, seedId, seedFieldId, t("helpTexts.seed"))}
            />

            {showMultimodalOptions && !useAgenticRetrieval && (
                <fieldset className={styles.fieldset + " " + styles.settingsSeparator}>
                    <legend className={styles.legend}>{t("labels.llmInputs")}</legend>
                    <Stack tokens={{ childrenGap: 8 }}>
                        <Checkbox
                            id="sendTextSources"
                            label={t("labels.llmInputsOptions.texts")}
                            checked={sendTextSources}
                            onChange={(_ev, checked) => {
                                onChange("sendTextSources", !!checked);
                            }}
                            onRenderLabel={props => renderLabel(props, "sendTextSourcesLabel", "sendTextSources", t("helpTexts.llmTextInputs"))}
                        />
                        <Checkbox
                            id="sendImageSources"
                            label={t("labels.llmInputsOptions.images")}
                            checked={sendImageSources}
                            onChange={(_ev, checked) => {
                                onChange("sendImageSources", !!checked);
                            }}
                            onRenderLabel={props => renderLabel(props, "sendImageSourcesLabel", "sendImageSources", t("helpTexts.llmImageInputs"))}
                        />
                    </Stack>
                </fieldset>
            )}
        </div>
    );
};
