import { useEffect, useState } from "react";
import { Stack, IDropdownOption, Dropdown, IDropdownProps } from "@fluentui/react";
import { useId } from "@fluentui/react-hooks";
import { useTranslation } from "react-i18next";

import styles from "./VectorSettings.module.css";
import { HelpCallout } from "../../components/HelpCallout";
import { RetrievalMode, VectorFields } from "../../api";

interface Props {
    showImageOptions?: boolean;
    defaultRetrievalMode: RetrievalMode;
    defaultVectorFields?: VectorFields;
    updateRetrievalMode: (retrievalMode: RetrievalMode) => void;
    updateVectorFields: (vectorFields: VectorFields) => void;
}

export const VectorSettings = ({ updateRetrievalMode, updateVectorFields, showImageOptions, defaultRetrievalMode, defaultVectorFields }: Props) => {
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(defaultRetrievalMode || RetrievalMode.Hybrid);
    const [vectorFields, setVectorFields] = useState<VectorFields>(defaultVectorFields || VectorFields.TextAndImageEmbeddings);

    const onRetrievalModeChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<RetrievalMode> | undefined) => {
        setRetrievalMode(option?.data || RetrievalMode.Hybrid);
        updateRetrievalMode(option?.data || RetrievalMode.Hybrid);
    };

    const onVectorFieldsChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<VectorFields> | undefined) => {
        setVectorFields(option?.data || VectorFields.TextAndImageEmbeddings);
        updateVectorFields(option?.data || VectorFields.TextAndImageEmbeddings);
    };

    // Only run if showImageOptions changes from true to false or false to true
    useEffect(() => {
        if (!showImageOptions) {
            // If images are disabled, we must force to text-only embeddings
            setVectorFields(VectorFields.Embedding);
            updateVectorFields(VectorFields.Embedding);
        } else {
            // When image options become available, reset to default or use TextAndImageEmbeddings
            setVectorFields(defaultVectorFields || VectorFields.TextAndImageEmbeddings);
            updateVectorFields(defaultVectorFields || VectorFields.TextAndImageEmbeddings);
        }
    }, [showImageOptions, updateVectorFields, defaultVectorFields]);

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
                <Dropdown
                    id={vectorFieldsFieldId}
                    label={t("labels.vector.label")}
                    selectedKey={vectorFields}
                    options={[
                        {
                            key: VectorFields.Embedding,
                            text: t("labels.vector.options.embedding"),
                            selected: vectorFields === VectorFields.Embedding,
                            data: VectorFields.Embedding
                        },
                        {
                            key: VectorFields.ImageEmbedding,
                            text: t("labels.vector.options.imageEmbedding"),
                            selected: vectorFields === VectorFields.ImageEmbedding,
                            data: VectorFields.ImageEmbedding
                        },
                        {
                            key: VectorFields.TextAndImageEmbeddings,
                            text: t("labels.vector.options.both"),
                            selected: vectorFields === VectorFields.TextAndImageEmbeddings,
                            data: VectorFields.TextAndImageEmbeddings
                        }
                    ]}
                    onChange={onVectorFieldsChange}
                    aria-labelledby={vectorFieldsId}
                    onRenderLabel={(props: IDropdownProps | undefined) => (
                        <HelpCallout labelId={vectorFieldsId} fieldId={vectorFieldsFieldId} helpText={t("helpTexts.vectorFields")} label={props?.label} />
                    )}
                />
            )}
        </Stack>
    );
};
