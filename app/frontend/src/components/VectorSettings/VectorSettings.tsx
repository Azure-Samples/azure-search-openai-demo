import { useEffect, useState } from "react";
import { Stack, IDropdownOption, Dropdown, IDropdownProps } from "@fluentui/react";
import { useId } from "@fluentui/react-hooks";
import { useTranslation } from "react-i18next";

import styles from "./VectorSettings.module.css";
import { HelpCallout } from "../../components/HelpCallout";
import { RetrievalMode, VectorFieldOptions } from "../../api";

interface Props {
    showImageOptions?: boolean;
    defaultRetrievalMode: RetrievalMode;
    updateRetrievalMode: (retrievalMode: RetrievalMode) => void;
    updateVectorFields: (options: VectorFieldOptions[]) => void;
}

export const VectorSettings = ({ updateRetrievalMode, updateVectorFields, showImageOptions, defaultRetrievalMode }: Props) => {
    const [retrievalMode, setRetrievalMode] = useState<RetrievalMode>(RetrievalMode.Hybrid);
    const [vectorFieldOption, setVectorFieldOption] = useState<VectorFieldOptions>(VectorFieldOptions.Both);

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
    const retrievalModeFieldId = useId("retrievalModeField");
    const vectorFieldsId = useId("vectorFields");
    const vectorFieldsFieldId = useId("vectorFieldsField");
    const { t } = useTranslation();

    return (
        <Stack className={styles.container} tokens={{ childrenGap: 10 }}>
            <Dropdown
                id={retrievalModeFieldId}
                label={t("settingsLabels.retrievalMode.label")}
                selectedKey={defaultRetrievalMode.toString()}
                options={[
                    { key: "hybrid", text: t("settingsLabels.retrievalMode.options.hybrid"), selected: retrievalMode == RetrievalMode.Hybrid, data: RetrievalMode.Hybrid },
                    { key: "vectors", text: t("settingsLabels.retrievalMode.options.vectors"), selected: retrievalMode == RetrievalMode.Vectors, data: RetrievalMode.Vectors },
                    { key: "text", text: t("settingsLabels.retrievalMode.options.texts"), selected: retrievalMode == RetrievalMode.Text, data: RetrievalMode.Text }
                ]}
                required
                onChange={onRetrievalModeChange}
                aria-labelledby={retrievalModeId}
                onRenderLabel={(props: IDropdownProps | undefined) => (
                    <HelpCallout labelId={retrievalModeId} fieldId={retrievalModeFieldId} helpText={t("toolTipText.retrievalMode")} label={props?.label} />
                )}
            />

            {showImageOptions && [RetrievalMode.Vectors, RetrievalMode.Hybrid].includes(retrievalMode) && (
                <Dropdown
                    id={vectorFieldsFieldId}
                    label={t("settingsLabels.vector.label")}
                    options={[
                        { key: VectorFieldOptions.Embedding, text: t("settingsLabels.vector.options.embedding"), selected: vectorFieldOption === VectorFieldOptions.Embedding },
                        { key: VectorFieldOptions.ImageEmbedding, text: t("settingsLabels.vector.options.imageEmbedding"), selected: vectorFieldOption === VectorFieldOptions.ImageEmbedding },
                        { key: VectorFieldOptions.Both, text: t("settingsLabels.vector.options.both"), selected: vectorFieldOption === VectorFieldOptions.Both }
                    ]}
                    onChange={onVectorFieldsChange}
                    aria-labelledby={vectorFieldsId}
                    onRenderLabel={(props: IDropdownProps | undefined) => (
                        <HelpCallout labelId={vectorFieldsId} fieldId={vectorFieldsFieldId} helpText={t("toolTipText.vectorFields")} label={props?.label} />
                    )}
                />
            )}
        </Stack>
    );
};
