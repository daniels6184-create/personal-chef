import '@fontsource-variable/inter';
import '@fontsource-variable/fraunces';
import './app.css';
import { mount } from 'svelte';
import App from './App.svelte';

mount(App, { target: document.getElementById('app') });
