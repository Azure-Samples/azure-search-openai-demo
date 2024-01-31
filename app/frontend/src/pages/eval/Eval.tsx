import { useEffect, useRef, useState } from "react";

export function Component(): JSX.Element {
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [data, setData] = useState<any>({});

    useEffect(() => {
        try {
            setIsLoading(true);

            // Retrieve Data from Endpoint
        } catch (e) {
        } finally {
            setIsLoading(false);
        }
    });

    return <div>Hello</div>;
}
