import { useState, useEffect } from "react";

interface Props {
    onBatchClicked: (id: number) => void;
}

const BatchSelect = ({ onBatchClicked }: Props) => {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [data, setData] = useState<any>({});

    useEffect(() => {
        const fetchData = async () => {
            try {
                setIsLoading(true);
                console.log("Fetching Data");
                const response = await fetch("/experiment_list");
                const jsonData = await response.json();
                setData(jsonData);
                console.log(data);
                setIsLoading(false);
            } catch (e) {
                console.log(e);
            }
        };

        fetchData();
    }, []);

    console.log(data);

    return (
        <div>
            {data.experiment_names.map(experiment => {
                <div>{experiment}</div>;
            })}
        </div>
    );
};
export default BatchSelect;
