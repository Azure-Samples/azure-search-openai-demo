import React, { useState } from 'react';
import { Stack, TextField, PrimaryButton, Dropdown, IDropdownOption, Text, Link } from '@fluentui/react';

import { Checkbox, Panel, DefaultButton, ITextFieldProps, ICheckboxProps } from "@fluentui/react";
import { SparkleFilled } from "@fluentui/react-icons";
import { useId } from "@fluentui/react-hooks";
import readNDJSONStream from "ndjson-readablestream";

import {
  chatApi,
  configApi,
  getSpeechApi,
  RetrievalMode,
  ChatAppResponse,
  ChatAppResponseOrError,
  ChatAppRequest,
  ResponseMessage,
  VectorFieldOptions,
  GPT4VInput,
  searchDocuments
} from "../../api";

import styles from "./SearchTab.module.css";


// Types
enum SearchType {
    Keyword = 'keyword',
    Vector = 'vector',
    Hybrid = 'hybrid'
}

interface SearchResult {
    title: string;
    content: string;
    url: string;
}


// Main component
const SearchTab: React.FC = () => {
    const [query, setQuery] = useState<string>('');
    const [searchType, setSearchType] = useState<SearchType>(SearchType.Hybrid);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);
    const [searchResults, setSearchResults] = useState<SearchResult[]>([]);

    const searchTypeOptions: IDropdownOption[] = [
        { key: SearchType.Keyword, text: 'Keyword' },
        { key: SearchType.Vector, text: 'Vector' },
        { key: SearchType.Hybrid, text: 'Hybrid' },
    ];

    const handleSearch = async () => {
      if (query.trim()) {
        setIsLoading(true);
        setError(null);
  
        try {
          const results = await searchDocuments(query, searchType);
          setSearchResults(results);
        } catch (e) {
          console.error('Error performing search:', e);
          setError(e instanceof Error ? e.message : 'An unknown error occurred');
        } finally {
          setIsLoading(false);
        }
      }
    };

    return (
        <Stack verticalAlign="start" className="search-container">
            <Stack horizontal tokens={{ childrenGap: 10 }}>
                <TextField
                    placeholder="Enter your search query"
                    value={query}
                    onChange={(_, newValue) => setQuery(newValue || '')}
                    disabled={isLoading}
                />
                <Dropdown
                    selectedKey={searchType}
                    options={searchTypeOptions}
                    onChange={(_, option) => option && setSearchType(option.key as SearchType)}
                    disabled={isLoading}
                />
                <PrimaryButton text="Search" onClick={handleSearch} disabled={isLoading} />
            </Stack>

            {isLoading && <Text>Loading results...</Text>}
            {error && <Text className="error-message">{error}</Text>}
            {!isLoading && !error && searchResults.length === 0 && (
                <Text>No results found. Try a different search query.</Text>
            )}
            {searchResults.length > 0 && (
                <Stack tokens={{ childrenGap: 10 }}>
                    {searchResults.map((result, index) => (
                        <Stack key={index} className="search-result">
                            <Link href={result.url} target="_blank" rel="noopener noreferrer">
                                {result.title}
                            </Link>
                            <Text>{result.content}</Text>
                        </Stack>
                    ))}
                </Stack>
            )}
        </Stack>
    );
};

export default SearchTab;