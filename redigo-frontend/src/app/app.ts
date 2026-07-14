import { Component } from '@angular/core';
import { SummaryComponent } from './components/summary/summary';

@Component({
  selector: 'app-root',
  imports: [SummaryComponent],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {}
