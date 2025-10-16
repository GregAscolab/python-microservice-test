import React from 'react';
import {render, fireEvent, waitFor} from '@testing-library/react-native';
import App from '../App';

// Mock the global fetch function
global.fetch = jest.fn();

// Mock the config module
jest.mock('../src/config', () => ({
  API_URL: 'http://mock-api.com',
}));

describe('App component', () => {
  beforeEach(() => {
    // Clear all mocks before each test
    fetch.mockClear();
  });

  it('renders the initial UI correctly', () => {
    const {getByText, queryByTestId} = render(<App />);
    expect(getByText('Owasys CAN Monitor')).toBeTruthy();
    expect(getByText('Fetch Log Files')).toBeTruthy();
    expect(queryByTestId('flat-list')).toBeNull();
  });

  it('fetches and displays data in a list on button press', async () => {
    const mockData = {
      contents: [
        {name: 'log1.txt', type: 'file'},
        {name: 'log2.txt', type: 'file'},
      ],
    };
    fetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const {getByText, findByText} = render(<App />);

    fireEvent.press(getByText('Fetch Log Files'));

    // Wait for the list items to appear
    await waitFor(() => {
      expect(findByText('log1.txt')).toBeTruthy();
      expect(findByText('log2.txt')).toBeTruthy();
    });
  });

  it('displays an error message when the fetch fails', async () => {
    const errorMessage = 'Network request failed';
    fetch.mockRejectedValueOnce(new Error(errorMessage));

    const {getByText} = render(<App />);

    fireEvent.press(getByText('Fetch Log Files'));

    // Wait for the component to update with the error message
    await waitFor(() => {
      expect(getByText(`Failed to fetch data. Please ensure the backend service is running and accessible. Error: ${errorMessage}`)).toBeTruthy();
    });
  });
});