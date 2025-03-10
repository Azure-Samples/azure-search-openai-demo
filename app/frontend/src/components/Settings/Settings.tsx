import { useId } from "@fluentui/react-hooks";
import { useTranslation } from "react-i18next";
import { TextField, ITextFieldProps, Checkbox, ICheckboxProps, Dropdown, IDropdownProps, IDropdownOption } from "@fluentui/react";
import { HelpCallout } from "../HelpCallout";
import { GPT4VSettings } from "../GPT4VSettings";
import { VectorSettings } from "../VectorSettings";
import { RetrievalMode, VectorFieldOptions, GPT4VInput } from "../../api";
import styles from "./Settings.module.css";

// Add type for onRenderLabel
type RenderLabelType = ITextFieldProps | IDropdownProps | ICheckboxProps;

export interface SettingsProps {
    promptTemplate: string;
    temperature: number;
    retrieveCount: number;
    seed: number | null;
    minimumSearchScore: number;
    minimumRerankerScore: number;
    useSemanticRanker: boolean;
    useSemanticCaptions: boolean;
    useQueryRewriting: boolean;
    excludeCategory: string;
    includeCategory: string;
    retrievalMode: RetrievalMode;
    useGPT4V: boolean;
    gpt4vInput: GPT4VInput;
    vectorFieldList: VectorFieldOptions[];
    showSemanticRankerOption: boolean;
    showQueryRewritingOption: boolean;
    showGPT4VOptions: boolean;
    showVectorOption: boolean;
    useOidSecurityFilter: boolean;
    useGroupsSecurityFilter: boolean;
    useLogin: boolean;
    loggedIn: boolean;
    requireAccessControl: boolean;
    className?: string;
    onChange: (field: string, value: any) => void;
    shouldStream?: boolean; // Only used in Chat
    useSuggestFollowupQuestions?: boolean; // Only used in Chat
    promptTemplatePrefix?: string;
    promptTemplateSuffix?: string;
    showSuggestFollowupQuestions?: boolean;
}

export const Settings = ({
    promptTemplate,
    temperature,
    retrieveCount,
    seed,
    minimumSearchScore,
    minimumRerankerScore,
    useSemanticRanker,
    useSemanticCaptions,
    useQueryRewriting,
    excludeCategory,
    includeCategory,
    retrievalMode,
    useGPT4V,
    gpt4vInput,
    vectorFieldList,
    showSemanticRankerOption,
    showQueryRewritingOption,
    showGPT4VOptions,
    showVectorOption,
    useOidSecurityFilter,
    useGroupsSecurityFilter,
    useLogin,
    loggedIn,
    requireAccessControl,
    className,
    onChange,
    shouldStream,
    useSuggestFollowupQuestions,
    promptTemplatePrefix,
    promptTemplateSuffix,
    showSuggestFollowupQuestions
}: SettingsProps) => {
    const { t } = useTranslation();

    // Form field IDs
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
    const queryRewritingFieldId = useId("queryRewritingField");
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

            {showSemanticRankerOption && (
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

            {showQueryRewritingOption && (
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

            {showGPT4VOptions && (
                <GPT4VSettings
                    gpt4vInputs={gpt4vInput}
                    isUseGPT4V={useGPT4V}
                    updateUseGPT4V={val => onChange("useGPT4V", val)}
                    updateGPT4VInputs={val => onChange("gpt4vInput", val)}
                />
            )}

            {showVectorOption && (
                <VectorSettings
                    defaultRetrievalMode={retrievalMode}
                    showImageOptions={useGPT4V && showGPT4VOptions}
                    updateVectorFields={val => onChange("vectorFieldList", val)}
                    updateRetrievalMode={val => onChange("retrievalMode", val)}
                />
            )}

            {/* Streaming checkbox for Chat */}
            {shouldStream !== undefined && (
                <Checkbox
                    id={shouldStreamFieldId}
                    className={styles.settingsSeparator}
                    checked={shouldStream}
                    label={t("labels.shouldStream")}
                    onChange={(_ev, checked) => onChange("shouldStream", !!checked)}
                    aria-labelledby={shouldStreamId}
                    onRenderLabel={props => renderLabel(props, shouldStreamId, shouldStreamFieldId, t("helpTexts.streamChat"))}
                />
            )}

            {/* Followup questions checkbox for Chat */}
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
        </div>
    );
};
