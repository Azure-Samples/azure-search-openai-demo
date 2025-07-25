import { useEffect, useState } from "react";
import { Stack, IDropdownOption, Dropdown, Checkbox, IDropdownProps } from "@fluentui/react";
import { useId } from "@fluentui/react-hooks";
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

    const onRetrievalModeChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<RetrievalMode> | undefined) => {
        setRetrievalMode(option?.data || RetrievalMode.Hybrid);
        updateRetrievalMode(option?.data || RetrievalMode.Hybrid);
    };

    const onSearchTextEmbeddingsChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setSearchTextEmbeddings(checked || false);
        updateSearchTextEmbeddings(checked || false);
    };

    const onSearchImageEmbeddingsChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setSearchImageEmbeddings(checked || false);
        updateSearchImageEmbeddings(checked || false);
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

    const retrievalModeId = useId("retrievalMode");
    const retrievalModeFieldId = useId("retrievalModeField");
    const vectorFieldsId = useId("vectorFields");
    const vectorFieldsFieldId = useId("vectorFieldsField");
    const { t } = useTranslation();

    return (
        <Stack className={styles.container} tokens={{ childrenGap: 10 }}>
            <Dropdown
                id={retrievalModeFieldId}
                label={t("labels.retrievalMode.label")}
                selectedKey={retrievalMode.toString()}
                options={[
                    {
                        key: "hybrid",
                        text: t("labels.retrievalMode.options.hybrid"),
                        selected: retrievalMode == RetrievalMode.Hybrid,
                        data: RetrievalMode.Hybrid
                    },
                    {
                        key: "vectors",
                        text: t("labels.retrievalMode.options.vectors"),
                        selected: retrievalMode == RetrievalMode.Vectors,
                        data: RetrievalMode.Vectors
                    },
                    { key: "text", text: t("labels.retrievalMode.options.texts"), selected: retrievalMode == RetrievalMode.Text, data: RetrievalMode.Text }
                ]}
                required
                onChange={onRetrievalModeChange}
                aria-labelledby={retrievalModeId}
                onRenderLabel={(props: IDropdownProps | undefined) => (
                    <HelpCallout labelId={retrievalModeId} fieldId={retrievalModeFieldId} helpText={t("helpTexts.retrievalMode")} label={props?.label} />
                )}
            />

            {showImageOptions && [RetrievalMode.Vectors, RetrievalMode.Hybrid].includes(retrievalMode) && (
                <fieldset className={styles.fieldset}>
                    <legend className={styles.legend}>{t("labels.vector.label")}</legend>
                    <Stack tokens={{ childrenGap: 8 }}>
                        <Checkbox
                            id={vectorFieldsFieldId + "-text"}
                            label={t("labels.vector.options.embedding")}
                            checked={searchTextEmbeddings}
                            onChange={onSearchTextEmbeddingsChange}
                            aria-labelledby={vectorFieldsId + "-text"}
                            onRenderLabel={props => (
                                <HelpCallout
                                    labelId={vectorFieldsId + "-text"}
                                    fieldId={vectorFieldsFieldId + "-text"}
                                    helpText={t("helpTexts.textEmbeddings")}
                                    label={props?.label}
                                />
                            )}
                        />
                        <Checkbox
                            id={vectorFieldsFieldId + "-image"}
                            label={t("labels.vector.options.imageEmbedding")}
                            checked={searchImageEmbeddings}
                            onChange={onSearchImageEmbeddingsChange}
                            aria-labelledby={vectorFieldsId + "-image"}
                            onRenderLabel={props => (
                                <HelpCallout
                                    labelId={vectorFieldsId + "-image"}
                                    fieldId={vectorFieldsFieldId + "-image"}
                                    helpText={t("helpTexts.imageEmbeddings")}
                                    label={props?.label}
                                />
                            )}
                        />
                    </Stack>
                </fieldset>
            )}
        </Stack>
    );
};
