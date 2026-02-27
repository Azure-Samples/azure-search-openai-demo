import { useEffect, useId, useState } from "react";
import { Dropdown, Option, Checkbox } from "@fluentui/react-components";
import type { OptionOnSelectData, CheckboxOnChangeData } from "@fluentui/react-components";
import { useTranslation } from "react-i18next";

import styles from "./VectorSettings.module.css";
import { HelpCallout } from "../../components/HelpCallout";
import { RetrievalMode } from "../../api";

interface Props {
    showImageOptions?: boolean;
    defaultRetrievalMode: RetrievalMode;
    defaultSearchTextEmbeddings?: boolean;
    defaultSearchImageEmbeddings?: boolean;
    updateRetrievalMode: (retrievalMode: RetrievalMode) => void;
    updateSearchTextEmbeddings: (searchTextEmbeddings: boolean) => void;
    updateSearchImageEmbeddings: (searchImageEmbeddings: boolean) => void;
}

export const VectorSettings = ({
    updateRetrievalMode,
    updateSearchTextEmbeddings,
    updateSearchImageEmbeddings,
    showImageOptions,
    defaultRetrievalMode,
    defaultSearchTextEmbeddings = true,
    defaultSearchImageEmbeddings = true
}: Props) => {
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(defaultRetrievalMode || RetrievalMode.Hybrid);
    const [searchTextEmbeddings, setSearchTextEmbeddings] = useState<boolean>(defaultSearchTextEmbeddings);
    const [searchImageEmbeddings, setSearchImageEmbeddings] = useState<boolean>(defaultSearchImageEmbeddings);

    const onRetrievalModeChange = (_ev: any, data: OptionOnSelectData) => {
        const mode = (data.optionValue as RetrievalMode) || RetrievalMode.Hybrid;
        setRetrievalMode(mode);
        updateRetrievalMode(mode);
    };

    const onSearchTextEmbeddingsChange = (_ev: any, data: CheckboxOnChangeData) => {
        setSearchTextEmbeddings(!!data.checked);
        updateSearchTextEmbeddings(!!data.checked);
    };

    const onSearchImageEmbeddingsChange = (_ev: any, data: CheckboxOnChangeData) => {
        setSearchImageEmbeddings(!!data.checked);
        updateSearchImageEmbeddings(!!data.checked);
    };

    // Only run if showImageOptions changes from true to false or false to true
    useEffect(() => {
        if (!showImageOptions) {
            // If images are disabled, we must disable image embeddings
            setSearchImageEmbeddings(false);
            updateSearchImageEmbeddings(false);
        } else {
            // When image options become available, reset to default
            setSearchImageEmbeddings(defaultSearchImageEmbeddings);
            updateSearchImageEmbeddings(defaultSearchImageEmbeddings);
        }
    }, [showImageOptions, updateSearchImageEmbeddings, defaultSearchImageEmbeddings]);

    const retrievalModeId = useId();
    const retrievalModeFieldId = useId();
    const vectorFieldsId = useId();
    const vectorFieldsFieldId = useId();
    const { t } = useTranslation();

    return (
        <div className={styles.container} style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            <div className={styles.settingsField}>
                <HelpCallout
                    labelId={retrievalModeId}
                    fieldId={retrievalModeFieldId}
                    helpText={t("helpTexts.retrievalMode")}
                    label={t("labels.retrievalMode.label")}
                />
                <Dropdown
                    id={retrievalModeFieldId}
                    selectedOptions={[retrievalMode.toString()]}
                    value={
                        retrievalMode === RetrievalMode.Hybrid
                            ? t("labels.retrievalMode.options.hybrid")
                            : retrievalMode === RetrievalMode.Vectors
                              ? t("labels.retrievalMode.options.vectors")
                              : t("labels.retrievalMode.options.texts")
                    }
                    onOptionSelect={onRetrievalModeChange}
                    aria-labelledby={retrievalModeId}
                >
                    <Option value="hybrid">{t("labels.retrievalMode.options.hybrid")}</Option>
                    <Option value="vectors">{t("labels.retrievalMode.options.vectors")}</Option>
                    <Option value="text">{t("labels.retrievalMode.options.texts")}</Option>
                </Dropdown>
            </div>

            {showImageOptions && [RetrievalMode.Vectors, RetrievalMode.Hybrid].includes(retrievalMode) && (
                <fieldset className={styles.fieldset}>
                    <legend className={styles.legend}>{t("labels.vector.label")}</legend>
                    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                        <div style={{ display: "flex", alignItems: "center" }}>
                            <Checkbox
                                id={vectorFieldsFieldId + "-text"}
                                checked={searchTextEmbeddings}
                                onChange={onSearchTextEmbeddingsChange}
                                aria-labelledby={vectorFieldsId + "-text"}
                            />
                            <HelpCallout
                                labelId={vectorFieldsId + "-text"}
                                fieldId={vectorFieldsFieldId + "-text"}
                                helpText={t("helpTexts.textEmbeddings")}
                                label={t("labels.vector.options.embedding")}
                            />
                        </div>
                        <div style={{ display: "flex", alignItems: "center" }}>
                            <Checkbox
                                id={vectorFieldsFieldId + "-image"}
                                checked={searchImageEmbeddings}
                                onChange={onSearchImageEmbeddingsChange}
                                aria-labelledby={vectorFieldsId + "-image"}
                            />
                            <HelpCallout
                                labelId={vectorFieldsId + "-image"}
                                fieldId={vectorFieldsFieldId + "-image"}
                                helpText={t("helpTexts.imageEmbeddings")}
                                label={t("labels.vector.options.imageEmbedding")}
                            />
                        </div>
                    </div>
                </fieldset>
            )}
        </div>
    );
};
