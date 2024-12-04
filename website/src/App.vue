<template>
  <div id="app">
    <nav>
      <ul>
        <!-- <li><router-link to="/">Home</router-link></li> -->
        <li><router-link to="/start">Quick Start</router-link></li>
        <li><router-link to="/advanced">Advanced</router-link></li>
      </ul>
    </nav>
    <router-view></router-view>
  </div>
</template>

<style>
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
</style>
