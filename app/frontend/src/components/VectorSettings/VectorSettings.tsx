import { useEffect, useState } from "react";
import { Stack, IDropdownOption, Dropdown, IDropdownProps } from "@fluentui/react";
import { useId } from "@fluentui/react-hooks";

import styles from "./VectorSettings.module.css";
import { HelpCallout } from "../../components/HelpCallout";
import { RetrievalMode, VectorFieldOptions } from "../../api";
import { toolTipText } from "../../i18n/tooltips.js";

interface Props {
    showImageOptions?: boolean;
    updateRetrievalMode: (retrievalMode: RetrievalMode) => void;
    updateVectorFields: (options: VectorFieldOptions[]) => void;
}

export const VectorSettings = ({ updateRetrievalMode, updateVectorFields, showImageOptions }: Props) => {
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    const [vectorFieldOption, setVectorFieldOption] = useState<VectorFieldOptions>(VectorFieldOptions.Embedding);

    const onRetrievalModeChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<RetrievalMode> | undefined) => {
        setRetrievalMode(option?.data || RetrievalMode.Hybrid);
        updateRetrievalMode(option?.data || RetrievalMode.Hybrid);
    };

    const onVectorFieldsChange = (_ev: React.FormEvent<HTMLDivElement>, option?: IDropdownOption<RetrievalMode> | undefined) => {
        setVectorFieldOption(option?.key as VectorFieldOptions);
        updateVectorFields([option?.key as VectorFieldOptions]);
    };

    useEffect(() => {
        showImageOptions
            ? updateVectorFields([VectorFieldOptions.Embedding, VectorFieldOptions.ImageEmbedding])
            : updateVectorFields([VectorFieldOptions.Embedding]);
    }, [showImageOptions]);

    const retrievalModeId = useId("retrievalMode");
    const vectorFieldsId = useId("vectorFields");

    return (
        <Stack className={styles.container} tokens={{ childrenGap: 10 }}>
            <Dropdown
                label="Retrieval mode"
                options={[
                    { key: "hybrid", text: "Vectors + Text (Hybrid)", selected: retrievalMode == RetrievalMode.Hybrid, data: RetrievalMode.Hybrid },
                    { key: "vectors", text: "Vectors", selected: retrievalMode == RetrievalMode.Vectors, data: RetrievalMode.Vectors },
                    { key: "text", text: "Text", selected: retrievalMode == RetrievalMode.Text, data: RetrievalMode.Text }
                ]}
                required
                onChange={onRetrievalModeChange}
                aria-labelledby={retrievalModeId}
                onRenderLabel={(props: IDropdownProps | undefined) => (
                    <HelpCallout id={retrievalModeId} helpText={toolTipText.retrievalMode} label={props?.label} />
                )}
            />

            {showImageOptions && [RetrievalMode.Vectors, RetrievalMode.Hybrid].includes(retrievalMode) && (
                <Dropdown
                    label="Vector fields (Multi-query vector search)"
                    options={[
                        { key: VectorFieldOptions.Embedding, text: "Text Embeddings", selected: vectorFieldOption === VectorFieldOptions.Embedding },
                        { key: VectorFieldOptions.ImageEmbedding, text: "Image Embeddings", selected: vectorFieldOption === VectorFieldOptions.ImageEmbedding },
                        { key: VectorFieldOptions.Both, text: "Text and Image embeddings", selected: vectorFieldOption === VectorFieldOptions.Both }
                    ]}
                    onChange={onVectorFieldsChange}
                    aria-labelledby={vectorFieldsId}
                    onRenderLabel={(props: IDropdownProps | undefined) => (
                        <HelpCallout id={vectorFieldsId} helpText={toolTipText.vectorFields} label={props?.label} />
                    )}
                />
            )}
        </Stack>
    );
};
