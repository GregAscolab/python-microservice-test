import React, {useState} from 'react';
import {
  SafeAreaView,
  StyleSheet,
  Text,
  View,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
} from 'react-native';
import {API_URL} from './src/config';

const App = () => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const response = await fetch(`${API_URL}/files/logger/`);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Network response was not ok. Status: ${response.status}. Message: ${errorText}`);
      }

      const json = await response.json();
      setData(json.contents); // We are interested in the 'contents' array
    } catch (e) {
      console.error(e);
      setError(`Failed to fetch data. Please ensure the backend service is running and accessible. Error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const renderItem = ({item}) => (
    <View style={styles.item}>
      <Text style={styles.itemText}>{item.name}</Text>
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Owasys CAN Monitor</Text>
      </View>
      <View style={styles.content}>
        <TouchableOpacity style={styles.button} onPress={fetchData} disabled={loading}>
          <Text style={styles.buttonText}>Fetch Log Files</Text>
        </TouchableOpacity>
        {loading && <ActivityIndicator size="large" color="#6200EE" />}
        {error && <Text style={styles.errorText}>{error}</Text>}
        {data && (
          <FlatList
            data={data}
            renderItem={renderItem}
            keyExtractor={item => item.name}
            style={styles.list}
          />
        )}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#F5F5F5',
  },
  header: {
    padding: 20,
    backgroundColor: '#6200EE',
    alignItems: 'center',
  },
  title: {
    fontSize: 24,
    color: 'white',
    fontWeight: 'bold',
  },
  content: {
    flex: 1,
    padding: 20,
  },
  button: {
    backgroundColor: '#6200EE',
    padding: 15,
    borderRadius: 5,
    alignItems: 'center',
    marginBottom: 20,
  },
  buttonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  list: {
    flex: 1,
  },
  item: {
    backgroundColor: 'white',
    padding: 20,
    marginVertical: 8,
    borderRadius: 5,
  },
  itemText: {
    fontSize: 16,
  },
  errorText: {
    color: 'red',
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 10,
  },
});

export default App;