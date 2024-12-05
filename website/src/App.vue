<template>
  <div id="app">
    <nav>
      <ul>
        <li><router-link to="/start">Quick Start</router-link></li>
        <li><router-link to="/advanced">Advanced</router-link></li>
      </ul>
    </nav>
    <main class="content">
      <router-view></router-view>
    </main>
    <footer>
      <p>
        Developed by
        <a href="https://morris88826.github.io" target="_blank">Mu-Ruei Tseng</a
        >. Have questions? Please contact
        <a href="mailto:morris88826@gmail.com">morris88826@gmail.com</a>.
      </p>
    </footer>
  </div>
</template>

<style scoped>
/* Root app styles */
#app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* Navbar styles */
nav {
  background-color: #333;
  padding: 1.5rem;
  display: flex;
  justify-content: center;
}

ul {
  list-style: none;
  display: flex;
  gap: 2rem;
  margin: 0;
  padding: 0;
}

li {
  display: inline;
  font-weight: bold;
}

a {
  color: white;
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

/* Main content styles */
.content {
  flex: 1; /* Pushes the footer to the bottom */
  padding: 1.5rem;
}

/* Footer styles */
footer {
  background-color: #222;
  color: #ddd;
  text-align: center;
  margin-top: auto;
}

footer a {
  color: #ddd;
  text-decoration: none;
  font-weight: bold;
}

footer a:hover {
  color: #fff;
  text-decoration: underline;
}

p {
  margin: 0;
  padding: 1.5rem;
}
</style>
