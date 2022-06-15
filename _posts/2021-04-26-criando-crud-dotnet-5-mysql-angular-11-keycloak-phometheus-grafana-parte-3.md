---
layout: post
title:  "Criando um CRUD com .NET 5, MySQL, Angular 11, Keycloak, Phometheus e Grafana — Parte 3"
author: alan
categories: [ On-Premise ]
tags: [ Angular, Keycloak, docker ]
image: assets/images/crud-3.gif
---
Nesse artigo vamos criar uma aplicação angular capaz de se autenticar em um servidor keycloak e usar essa autenticação para consumir uma API para listar, incluir, editar e excluir produtos.

## Criando o projeto

Para criar o nosso projeto vamos utilizar o Angular CLI, para vamos executar o seguinte comando na raiz do nosso repositório:

```plaintext
ng new frontend --skip-tests
```

Vamos utilizar o parâmetro --skip-tests no momento pois não vamos escrever casos de teste.

![Opções do Angular CLI](/assets/images/crud-3-ng-new.png "Opções do Angular CLI")

Nesse caso aceitei usar Angular Routing e selecionei CSS como nossa ferramenta para estilização.

## Configurando ambiente

Podemos configurar o endereço do nosso servidor keycloak e da nossa api nos arquivos environment.prod.ts e invironment.ts:

```typescript
export const environment = {
  production: true,
  apiUrl: 'http://localhost:5000',
  keycloak: {
        url: 'http://keycloak:8080/auth',
        realm: 'products_api',
        clientId: 'api',
  }
};
```

```typescript
export const environment = {
  production: false,
  apiUrl: 'http://localhost:5000',
  keycloak: {
        url: 'http://keycloak:8080/auth',
        realm: 'products_api',
        clientId: 'api',
  }
};
```

## Instalando dependências

Nesse projeto vamos utilizar a biblioteca keycloak-angular, ela vai auxiliar na implementação do nosso AuthGuard e da interceptação das requisições do HttpClient. Podemos realizar a instalação executando o seguinte comando na pasta da nossa aplicação angular(frontend):

```plaintext
npm install keycloak-angular keycloak-js --save
```

## Criando componentes do Keycloak-Angular

Para configurar a nossa autenticação vamos criar uma pasta chamada auth dentro da pasta app da nossa aplicação, o caminho dessa pasta deve ser:

```plaintext
frontend\src\app\auth 
```

Dentro dessa nova pasta vamos criar o arquivo keycloak-initializer.ts:

```typescript
import { KeycloakService } from 'keycloak-angular';

import { environment } from '../../environments/environment';

export function keycloakInitializer(keycloak: KeycloakService): () => Promise<any> {
    return (): Promise<any> => {
        return new Promise(async (resolve, reject) => {
            try {
                await keycloak.init({
                    config: environment.keycloak,
                    initOptions: {
                        checkLoginIframe: false
                    },
                    bearerExcludedUrls: []
                });
                resolve(null);
            } catch (error) {
                reject(error);
            }
        });
    };
}
```

Esse arquivo contém uma função que será usada para configurar o keycloak no inicio da execução da aplicação.

Também na pasta auth vamos criar o arquivo auth-guard.ts:

```typescript
import { Injectable } from '@angular/core';
import { ActivatedRouteSnapshot, Router, RouterStateSnapshot } from '@angular/router';
import { KeycloakAuthGuard, KeycloakService } from 'keycloak-angular';

@Injectable({
  providedIn: 'root'
})
export class AuthGuard extends KeycloakAuthGuard {
  constructor(protected router: Router, protected keycloakAngular: KeycloakService) {
    super(router, keycloakAngular);
  }
  isAccessAllowed(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Promise<boolean> {
    return new Promise(async (resolve) => {
      if (!this.authenticated) {
        this.keycloakAngular.login();
        resolve(false);
      }
      resolve(true);
    });
  }
}
```

Essa classe vai ser configurada como uma proteção para nossas rotas, sendo assim, se estivermos autenticados vamos poder seguir para a tela solicitada, caso contrário seremos redirecionados para a tela de login.

## Criando estrutura de roteamento de componentes

Para criar nossa estrutura de roteamentos primeiro precisamos que nossos componentes sejam criados. Vamos abrir o terminal na pasta frontend e executar os seguintes comandos:

```plaintext
ng generate component header
ng generate component products-list
ng generate component product-form
```

Agora podemos configurar nosso arquivo app-routing.module.ts:

```typescript
import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { AuthGuard } from './auth/auth-guard';
import { ProductFormComponent } from './product-form/product-form.component';
import { ProductsListComponent } from './products-list/products-list.component';

const routes: Routes = [
  { path: '', pathMatch:'full', redirectTo: 'products' },
  { 
    path: 'products',
    component: ProductsListComponent,
    canActivate: [AuthGuard] 
  },
  { 
    path: 'products/:id/edit',
    component: ProductFormComponent,
    canActivate: [AuthGuard] 
  },
  { 
    path: 'products/new',
    component: ProductFormComponent,
    canActivate: [AuthGuard] 
  },
  { path: '**', redirectTo: '' }
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule { }
```

## Configurando keycloak no App.Module

Precisamos importar o módulo _KeycloakAngularModule_, declarar um provider do tipo APP_INITIALIZER para o nosso _keycloakInitializer_ e um provider para nosso AuthGuard.

Também vamos importar os módulos _HttpClientModule_ e _FormsModule_ que são usados ao longo da aplicação, nosso app.module.ts deve estar assim:

```typescript
import { BrowserModule } from '@angular/platform-browser';
import { APP_INITIALIZER, NgModule } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClientModule } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { HeaderComponent } from './header/header.component';
import { ProductsListComponent } from './products-list/products-list.component';
import { ProductFormComponent } from './product-form/product-form.component';
import { KeycloakAngularModule, KeycloakService } from 'keycloak-angular';
import { keycloakInitializer } from './auth/keycloak-initializer';
import { AuthGuard } from './auth/auth-guard';

@NgModule({
  declarations: [
    AppComponent,
    HeaderComponent,
    ProductsListComponent,
    ProductFormComponent
  ],
  imports: [
    BrowserModule,
    AppRoutingModule,
    KeycloakAngularModule,
    HttpClientModule,
    FormsModule
  ],
  providers: [{
    provide: APP_INITIALIZER,
    useFactory: keycloakInitializer,
    multi: true,
    deps: [KeycloakService]
  },
  AuthGuard
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
```

## Requisitando a API

Vamos criar uma classe que vai representar nosso produto, para isso podemos executar o seguinte comando na pasta frontend:

```plaintext
ng generate class models/product
```

Podemos adicionar as propriedades do nosso produto, ficando com a classe assim:

```typescript
export class Product {
    id?: string;
    productName: string = ``;
    sku: string = ``;
    upc: string = ``;
    price: number = 0;
};
```

E criaremos um service para requisitar nossos endpoints da API, podemos fazer isso executando o comando:

```plaintext
ng generate service api/product
```

Nosso service pode ser implementado da seguinte forma:

```typescript
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { environment } from 'src/environments/environment';
import { Product } from '../models/product';


@Injectable({
  providedIn: 'root'
})
export class ProductService {

  apiUrl:string = environment.apiUrl;

  constructor(private http: HttpClient) { }

  getAll(){
    return this.http.get<Product[]>(`${this.apiUrl}/products`);
  }

  getById(id: string){
    return this.http.get<Product>(`${this.apiUrl}/products/${id}`);
  }

  insert(product: Product){
    return this.http.post(`${this.apiUrl}/products/`, product);
  }

  update(product: Product){
    return this.http.put(`${this.apiUrl}/products/${product.id}`, product);
  }

  delete(id: string){
    return this.http.delete(`${this.apiUrl}/products/${id}`);
  }
}
```

## Criando componentes visuais

Vamos começar definindo estilos comuns da aplicação no arquivo styles.css:

```css
/* You can add global styles to this file, and also import other style files */

:root {
    --primary-color: #bf7d06;
    --primary-color-light: rgb(248, 221, 170);
    --default-text-color: #231701;
}

body{
    margin: 0px;
    font-family: sans-serif;
    color: var(--default-text-color)
}

.applicationButton{
    background-color: var(--primary-color);
    border: 1px solid white;
    color: white;
}
```

O próximo componente que alteraremos é o App.Component, que passa a somente exibir o Header.Component e servir como container para outras telas:

```css
.container{
    display: flex;
    justify-content: center;
}
```

```html
<div class="nav">
  <app-header></app-header>
</div>

<div class='container'>
  <router-outlet></router-outlet>
</div>
```

Nosso Header.Component fica sendo responsável por requisitar o logout da aplicação e pode ser implementado da seguinte maneira:

```css
.headerArea{
    background:  var(--primary-color);
    height: 35px;
    display: flex;
    flex-direction: row;
    justify-content: space-between;
    align-items: center;
}

.title{
    color: white;
    font-size: 20px;
    margin: 0px 0px 0px 10px;
}


.headerButton{
    margin-right: 10px;
    width: 100px;
    height: 25px;
}
```

```html
<div class='headerArea'>
    <h1 class='title'>Product Management</h1>
    <button class='headerButton applicationButton' (click)="logout()">Logout</button>
</div>
```

```typescript
import { Component, OnInit } from '@angular/core';
import { KeycloakService } from 'keycloak-angular';

@Component({
  selector: 'app-header',
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.css']
})
export class HeaderComponent implements OnInit {

  constructor(private keycloakAngular: KeycloakService) { }

  ngOnInit(): void {
  }

  async logout() {
    this.keycloakAngular.logout();
  }

}
```

Podemos agora desenvolver o ProductsList.Component, que é responsável por listar, direcionar para inclusão/edição e apagar produtos.

O componente deve ficar assim:

```css
.componentArea{
    width: 800px;
}

.headerArea{
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: space-between;
}

.newButton{
    height: 25px;
    width: 100px;
}

.tableStyled{
    width: 100%;
}

.tableStyled thead tr{
    background-color: var(--primary-color);
    color: white;
}

.tableStyled tbody tr:nth-of-type(even) {
    background-color: var(--primary-color-light);
}

.actionButtonsArea{
    display: flex;
    flex-direction: row;
    justify-content: space-around;
}

.actionButton{
    height: 25px;
    width: 75px;
}
```

{% raw  %}

```html
<div class="componentArea">
    <div class="headerArea">
        <h1>Product list</h1>
        <button class="newButton applicationButton" (click)='createProduct()'>New</button>
    </div>

    <table class='tableStyled'>
        <thead>
            <tr>              
                <th>Product Name</th>
                <th>UPC</th>
                <th>SKU</th>
                <th>Price</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            <tr *ngFor="let product of products">
                <td>{{ product.productName }}</td>
                <td>{{ product.upc }}</td>
                <td>{{ product.sku }}</td>
                <td>{{ numberToCurrencyFormat(product.price) }}
                </td>
                <td>
                    <div class="actionButtonsArea">
                        <button class="actionButton applicationButton" (click)="editProduct(product.id!)" >Edit</button>
                        <button class="actionButton applicationButton" (click)="deleteProduct(product.id!)">Delete</button>
                    </div>
                </td>
            </tr>
        </tbody>
    </table>
    
</div>
```

{% endraw %}

```typescript
import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { Product } from '../models/product';
import { ProductService } from '../api/product.service';

@Component({
  selector: 'app-product-list',
  templateUrl: './products-list.component.html',
  styleUrls: ['./products-list.component.css']
})
export class ProductsListComponent implements OnInit {

  products: Product[] = [];

  constructor(private productService: ProductService, private router: Router) { }

  async ngOnInit() {
    await this.loadProducts();
  }

  loadProducts() {
    this.productService.getAll().subscribe(
      (products) => {
        this.products = products;
      },
      (error) => this.errorHandler(error)
    )
  }
  errorHandler(error: any): void {
    console.log(error);
  }

  editProduct(id: string){
    this.router.navigate([`products/${id}/edit`])
  }

  createProduct(){
    this.router.navigate([`products/new`])
  }

  async deleteProduct(id: string){
    if (window.confirm("Are you sure you want to delete this product?")){
      await this.productService.delete(id).toPromise();
      this.loadProducts();
    }
  }

  numberToCurrencyFormat(value: any){
    return new Intl.NumberFormat('en-US',{ style: 'currency', currency: 'USD' }).format(value) 
  }
}
```

Agora vamos ao componente ProductForm.component, que é responsável pela inclusão e edição de produtos. Ele foi implementado da seguinte maneira:

```css
.componentArea{
    width: 800px;
}

.inputArea{
    margin-bottom: 10px;
}

.inputArea label{
    display: block;
    width: 200px;
}

.inputArea input{
    display: block;;
    height: 30px;
    border: 1px solid var(--primary-color);
    border-radius: 15px;
    padding-left: 15px;
}

.error{
    color: red;
}

.saveButton{
    height: 35px;
    width: 200px;
    margin-right: 10px;
}

.cancelButton{
    height: 35px;
    width: 200px;
}
```

```html
<div class="componentArea">
    <h1>{{product?.productName}}</h1>

    <div *ngIf="product">
        <div class="inputArea">
            <label>Product Name:</label>
            <input type="text"  [(ngModel)]="product.productName"  />
            <span class='error'>{{errors.ProductName}}</span>
        </div>
        <div class="inputArea">
            <label>UPC</label>
            <input type="text" [(ngModel)]="product.upc" />
            <span class='error'>{{errors.UPC}}</span>
        </div>
        <div class="inputArea">
            <label>SKU</label>
            <input type="text"  [(ngModel)]="product.sku"  />
            <span class='error'>{{errors.SKU}}</span>
        </div>
        <div class="inputArea">
            <label>Price</label>
            <input type="number"  [(ngModel)]="product.price"  />
            <span class='error'>{{errors.Price}}</span>
        </div>

        <div class="buttonSaveArea">
            <button class='saveButton applicationButton' (click)='save()'>Save</button>
            <button class='cancelButton applicationButton' (click)='cancel()'>Cancel</button>
        </div>

    </div>
</div>
```

```typescript
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Product } from '../models/product';
import { ProductService } from '../api/product.service';

@Component({
  selector: 'app-product-form',
  templateUrl: './product-form.component.html',
  styleUrls: ['./product-form.component.css']
})
export class ProductFormComponent implements OnInit {

  productId: string = '';
  product: Product = new Product();
  errors: any = [];

  constructor(
    private route: ActivatedRoute,
    private productService: ProductService,
    private router: Router
    ) { }

  ngOnInit() {
    this.route.params.subscribe(async params =>  {
      this.productId = params['id'];
      if (this.productId){
        this.product = await this.productService.getById(this.productId).toPromise();
      }
   });
  }

  async save(){
    if(this.isNewProduct()){
      this.insertProduct();
    }else{
      this.updateProduct();
    }
  }

  private isNewProduct() {
    return !this.product.id;
  }

  insertProduct(){
    this.productService.insert(this.product).subscribe(
      () => this.navigateToProductsList(),
      error => this.handleError(error)
    );
  }

  updateProduct(){
    this.productService.update(this.product).subscribe(
      () => this.navigateToProductsList(),
      error => this.handleError(error)
    );
  }

  handleError(error: any) {
    console.log(error);
    this.errors = error.error?.errors;
  }

  cancel(){
    this.navigateToProductsList();
  }

  navigateToProductsList() {
    this.router.navigate(['products']);
  }

}
```

## Criando uma imagem para nosso frontend

Vamos começar criando o arquivo Dockerfile responsável pela construção da nossa imagem. O arquivo deve ser criado na pasta frontend e deve conter as seguintes instruções:

```dockerfile
# Build
FROM node:14-alpine as build-step
RUN mkdir -p /app
WORKDIR /app
COPY package.json /app
RUN npm install
COPY . /app
RUN npm run build -- --prod
 
# Runtime
FROM nginx:1.17.1-alpine as runtime-step
COPY --from=build-step /app/dist/frontend /usr/share/nginx/html
COPY ./nginx-custom.conf /etc/nginx/conf.d/default.conf
```

Nesse arquivo definimos que usaremos um container node para realizar o build da aplicação e um container nginx para executar nossa aplicação web.

Precisamos configurar o nginx para servir uma Single Page Application (SPA) e faremos isso com o arquivo nginx-custom.conf que deve ser criado na mesma pasta do Dockerfile:

```plaintext
server {
  listen 80;
  location / {
    root /usr/share/nginx/html;
    index index.html index.htm;
    try_files $uri $uri/ /index.html =404;
  }
}
```

Vamos criar um arquivo para definir arquivos que o docker deve ignorar, esse arquivo se chama .dockerignore e deve estar na pasta frontend:

```plaintext
/node_modules
.gitignore
```

## Configurando o docker-compose

Agora que temos uma imagem pronta para ser construída, podemos criar um service no arquivo docker-compose.yml:

```yaml
[...]
  frontend:
    depends_on:
      - api
    container_name: frontend
    build: frontend/.
    ports:
      - "4200:80"
    restart: always 
```

Podemos subir nossa infraestrutura com o comando:

```plaintext
docker-compose up -d --build
```

Depois de um ou dois minutos nossos serviços subiram e podemos abrir nossa aplicação em [http://localhost:4200/](http://localhost:4200/).

![Lista de Produtos](/assets/images/crud-3-product-list.png "Lista de Produtos")

E assim chegamos ao fim da parte funcional da aplicação, no próximo artigo vamos configurar o prometheus e acompanhar através do grafana o uso do nosso sistema!

Gostou? Tem alguma sugestão ou dúvida? Deixa ai nos comentários!

Segue o link do repositório no estado atual do projeto:

[Repositório Products Management](https://github.com/alanlviana/Products-Management/tree/v3)
