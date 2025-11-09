const axios = require('axios');

// Install axios: npm install axios

async function makePostRequest() {
  try {
    const response = await axios.post('http://localhost:8000/create-game', {
      owner: 'dsch',
      number_people: 8
    });
    console.log(response.data);
  } catch (error) {
    console.error(error);
  }
}

makePostRequest();