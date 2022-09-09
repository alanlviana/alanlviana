---
layout: post
title:  "Automatizando a criação de pipeline com .NET Core 6, AWS API Gateway e CDK"
author: alan
categories: [ AWS ]
tags: [ .netcore, api gateway, aws code commit, aws code build, aws code deploy, lambda, swagger ]
image: assets/images/pipeline-cdk-webapi-dotnet-core.png
---

Nesse artigo será apresentado uma solução para criação de um pipeline para uma Web API na AWS.

## Introdução

> "Que pipeline cria os pipelines?" - Viana, Alan

Entendo que é comum trabalharmos com pipelines automatizados, mas e quando precisamos automatizar essas automações? Essa dúvida me fez desenvolver um projeto e escrever esse texto.

Esse artigo tem como propósito possibilitar que apartir de uma linha de comando seja possível criar os seguintes recursos:
- Repositório de Código no AWS Code Commit
- Pipeline com Code Pipeline, Code Source, Code Build e Code Deploy
- Web API .NET Core 6 rodando em ambiente serverless com AWS Lambda
- Bucket S3 para armazenar versões de uma especificação Swagger
- AWS API Gateway com especificação e integração com Web API

Esse artigo envolve um ambiente de complexidade intermediária e o uso de diversas ferramentas que necessitam de configuração específicas. Tentei organizar da forma mais simples que consegui, mas ainda considero que ele é indicado para quem possui um conhecimento intermediário de desenvolvimento na AWS.

## Requisitos
Para que possamos começar com essa automação, é necessário:
- Possuir uma conta na AWS.
- Possuir o .NET Core SDK na versão 6.0 configurado no ambiente de desenvolvimento.
- AWS CDK configurado na máquina de desenvolvimento. É necessário que o bootstrap do AWS CDK já tenha sido realizado na conta. [Mais informações sobre CDK](https://aws.amazon.com/pt/getting-started/guides/setup-cdk/module-one/).
- Ter configurado o acesso ao Code Commit via SSH ou HTTPs.  [Mais informações sobre a configuração do Code Commit](https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-ssh-windows.html).

## Criando projeto com o AWS Cloud Development Kit (CDK)

Para esse projeto vamos utilizar typescript para interagir com definir nossa infraestrutura. Recomendo dentro do seu workspace seja executado o seguinte comando:

```bash
mkdir cdk-dotnet-api
cd cdk-dotnet-api
cdk init --language typescript
```

Será criada toda a estrutura do projeto, precisaremos criar recursos no arquivo _lib/cdk-dotnet-api-stack.ts_. Vamos alterar o arquivo para que fique da seguinte maneira:

```typescript
import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as codecommit from 'aws-cdk-lib/aws-codecommit';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cdk from 'aws-cdk-lib';

import { LinuxBuildImage } from 'aws-cdk-lib/aws-codebuild';

export class CdkDotnetApiStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // parameter of type String
    const apiName = this.node.tryGetContext('ApiName');

    // OpenApi Bucket
    const openApiBucket = new s3.Bucket(this, apiName+ 'OpenApi');

    // CodeCommit
    console.log('Creating repository.');
    const repository = new codecommit.Repository(this, apiName, {
      repositoryName: apiName
    });

    const sourceArtifact = new codepipeline.Artifact('SourceArtifact');
    const sourceAction = new codepipeline_actions.CodeCommitSourceAction({
      actionName: 'CodeCommit',
      repository: repository,
      output: sourceArtifact,
    });

    // Code Build
    console.log('Creating Build Action.');
    const projectName = apiName + 'Project';
    const project = new codebuild.PipelineProject(this, projectName, {
      projectName:projectName,
      environment: {
        buildImage: LinuxBuildImage.STANDARD_6_0
      }
    });
    const ssmPutParameterPolicy = new iam.PolicyStatement({
      actions: ['ssm:PutParameter'],
      resources: ['*'],
    });
    const s3PutObjectBucketsPolicy = new iam.PolicyStatement({
      actions: ['s3:PutObject'],
      resources: [openApiBucket.bucketArn+'/*'],
    });

    project.role?.attachInlinePolicy(new iam.Policy(this, 'open-api', {
      policyName: apiName+'OpenApiPolicy',
      statements: [s3PutObjectBucketsPolicy, ssmPutParameterPolicy]
    }))

    const buildArtifact = new codepipeline.Artifact('BuildArtifact');
    const buildAction = new codepipeline_actions.CodeBuildAction({
      actionName: 'CodeBuild',
      project,
      input: sourceArtifact,
      outputs: [buildArtifact],
      environmentVariables: {
        BucketOpenAPI: {
          type: codebuild.BuildEnvironmentVariableType.PLAINTEXT,
          value: openApiBucket.bucketName,
        },
        AWS_ACCOUNT_ID: {
          type: codebuild.BuildEnvironmentVariableType.PLAINTEXT,
          value: cdk.Stack.of(this).account,
        },
      }
    });

    // Code Deploy
    console.log('Creating deploy action.')
    const deployAction = new codepipeline_actions.CloudFormationCreateUpdateStackAction({
      actionName: 'Deploy',
      stackName: apiName + 'Stack',
      adminPermissions: true,
      replaceOnFailure: true,
      extraInputs: [buildArtifact],
      templatePath: sourceArtifact.atPath('template.yml'),
      parameterOverrides: {
        ApiName: apiName,
        BucketName: buildArtifact.bucketName,
        ObjectKey: buildArtifact.objectKey
      }
    })

    // Pipeline
    console.log('Creating pipeline.');
    var pipelineName = apiName + 'Pipeline' ;
    const pipeline = new codepipeline.Pipeline(this, pipelineName,{
      pipelineName: pipelineName,
      stages: [
        {
          stageName: 'Source',
          actions: [sourceAction]
        },
        {
          stageName: 'Build',
          actions: [buildAction]
        },
        {
          stageName: 'Deploy',
          actions: [deployAction]
        }

      ]
    });
  }
}
```

Nesse arquivo criamos os recursos que precisariam ser criados através do console da AWS, mas com uma automação. O mais interessante é que recebemos o nome da API que estamos criando no construtor, sendo assim esse script pode ser utilizado diversas vezes, sempre que quisermos criar rapidamente um novo pipeline. Para o exemplo vamos criar uma API de Weather com seguinte comando na raiz do projeto:

```bash
cdk deploy --context ApiName=Weather
```

## Iniciando o desenvolvimento da aplicação

Após a conclusão do deploy, o pipeline está criado e podemos clonar o repositório.

```bash
git clone ssh://git-codecommit.us-east-1.amazonaws.com/v1/repos/Weather
cd Weather
```

Iniciaremos criando uma api simples dentro do nosso repositório executando os seguintes comandos na raíz do repositório:

```bash
mkdir api
cd api
dotnet new webapi
dotnet new gitignore
dotnet add package AWSSDK.Extensions.NETCore.Setup --version 3.7.2
dotnet add package Amazon.Lambda.AspNetCoreServer.Hosting --version 1.3.1
```

Com isso temos a aplicação criada com as dependências necessárias para que seja possível executar o projeto no AWS Lambda. Também precisaremos adicionar a seguinte instrução no arquivo _Program.cs_ após o método _AddControllers_:

```csharp
builder.Services.AddControllers();
builder.Services.AddAWSLambdaHosting(LambdaEventSource.RestApi);
```

Com a aplicação criada, devemos criar o arquivo de integração que será usado pelo API Gateway. Criaremos o arquivo no caminho _aws-integrations/integrations.json_ com seguinte conteúdo:

```json
{
  "paths": {
    "/WeatherForecast": {
      "get": {
        "x-amazon-apigateway-auth": {
          "type": "none"
        },
        "x-amazon-apigateway-integration": {
          "x-amazon-apigateway-integration": null,
          "type": "aws_proxy",
          "uri": "arn:aws:apigateway:us-east-1:lambda:path/2015-03-31/functions/arn:aws:lambda:us-east-1:{AWS_ACCOUNT}:function:LambdaWeather/invocations",
          "httpMethod": "POST",
          "passthroughBehavior": "when_no_templates",
          "payloadFormatVersion": 1
        }
      }
    }
  }
}
```

Esse arquivo será incorporado a especificação swagger da nossa API, dessa forma o API Gateway conseguirá direcionar as requisições para o LambdaWeather que criaremos logo mais. Podemos agora iniciar a construção dos artefatos que a aplicação precisa para ser implantada. Faremos isso utilizando o arquivo _buildspec.yml_ na raiz do nosso repositório com o seguinte conteúdo:

```yml
version: 0.2
env:
  variables:
    BucketOpenAPI: "value"
    ProjectName: "api"
phases:
  install:
    runtime-versions:
      dotnet: 6.0
  pre_build:
    commands:
      - echo Build Number ${CODEBUILD_BUILD_NUMBER} 
      - echo Install Swagger CLI
      - dotnet new tool-manifest
      - dotnet tool install --version 6.2.3 Swashbuckle.AspNetCore.Cli
      - echo Project restore started on `date`
      - dotnet restore api/${ProjectName}.csproj
  build:
    commands:
      - echo Build started on `date`
      - dotnet build api/${ProjectName}.csproj
      - dotnet swagger tofile --output api/bin/Debug/net6.0/swagger-$CODEBUILD_BUILD_NUMBER.json api/bin/Debug/net6.0/api.dll v1
      - sed -i "s/{AWS_ACCOUNT}/$AWS_ACCOUNT_ID/g" aws-integrations/integrations.json
      - jq -s '.[0] as $a | .[1] as $b | $a * $b' api/bin/Debug/net6.0/swagger-$CODEBUILD_BUILD_NUMBER.json aws-integrations/integrations.json > swagger-with-integration.json
      - aws s3 cp swagger-with-integration.json s3://$BucketOpenAPI/swagger-$CODEBUILD_BUILD_NUMBER.json
      - aws ssm put-parameter --name "BucketOpenAPI" --type "String" --value $BucketOpenAPI --overwrite
      - aws ssm put-parameter --name "ObjectOpenAPI" --type "String" --value swagger-$CODEBUILD_BUILD_NUMBER.json --overwrite
  post_build:
    commands:
      - echo Publish started on `date`
      - dotnet publish -c Release -r linux-x64 -o ./publish api/${ProjectName}.csproj
artifacts:
  files:
    - '**/*'
  base-directory: './api/bin/Release/net6.0/linux-x64*'
  discard-paths: yes
```
Esse arquivo tem algumas funções importantes:
- Instalamos o swagger-cli para gerar a especificação da API apartir do código .net.
- Restauramos dependências do projeto para build.
- Realizamos o build da aplicação.
- Criamos um arquivo de especificação da API com o swagger-cli com base no resultado da compilação.
- Inserimos o número da conta da AWS no arquivo de integração utilizando o comando _sed_.
- Combinamos o arquivo de especificação da API com o arquivo de integração esperado pelo API Gateway.
- Fazemos uma cópia do arquivo final para um bucket S3 que mantém todas as versões da especificação. (Bucket também criado pela automação.)
- Inserimos o nome do bucket e o caminho do arquivo de especificação em parametros do ParameterStore que serão usados no deploy.
- Criamos um artefato com o resultado do build.

## Realizando o deploy

Podemos iniciar a criação do _template.yml_, que mantém a especificação dos recursos que nossa API precisa criar para ser executada. O arquivo vai ter o seguinte conteúdo:

```yml
AWSTemplateFormatVersion: '2010-09-09'
Description: Lambda API
Parameters:
  ApiName:
    Type: String
    Description: API Name
  BucketName:
    Type: String
    Description: Bucket name of Build Artifact.
  ObjectKey:
    Type: String
    Description: Bucket name of Build Artifact.
  BucketOpenAPI:
    Type: AWS::SSM::Parameter::Value<String>
    Default: /BucketOpenAPI
  ObjectOpenAPI:
    Type: AWS::SSM::Parameter::Value<String>
    Default: /ObjectOpenAPI
Resources:
  ApiGateway:
    Type: AWS::ApiGateway::RestApi
    Properties: 
      Name: !Join [ "", [ !Ref ApiName, "RestApi"] ]
      BodyS3Location: 
        Bucket: !Ref BucketOpenAPI
        Key: !Ref ObjectOpenAPI
      Description: A Rest API
    DependsOn: LambdaRestAPI

  LambdaRestAPIPermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref LambdaRestAPI
      Action: "lambda:InvokeFunction"
      Principal: "apigateway.amazonaws.com"
      SourceArn: !Sub arn:aws:execute-api:${AWS::Region}:${AWS::AccountId}:*
    DependsOn: LambdaRestAPI

  LambdaRestAPI:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: !Join [ "", [ "Lambda",!Ref ApiName] ]
      Runtime: dotnet6
      MemorySize: 4096
      Timeout: 30
      Role: !GetAtt LambdaRestApiExecutionRole.Arn
      Handler: api
      Code:
        S3Bucket: !Ref BucketName
        S3Key: !Ref ObjectKey
      Description: Rest API Lambda Function
      TracingConfig:
        Mode: Active
    DependsOn: LambdaRestApiExecutionRole

  LambdaRestApiExecutionRole:
    Type: 'AWS::IAM::Role'
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          - Effect: Allow
            Principal:
              Service:
                - lambda.amazonaws.com
            Action:
              - 'sts:AssumeRole'
      Path: /
      Policies:
        - PolicyName: ExecutionPolicy
          PolicyDocument:
            Version: "2012-10-17"
            Statement:
              - Effect: Allow
                Action: 
                  - "logs:CreateLogGroup"
                  - "logs:CreateLogStream"
                  - "logs:PutLogEvents"
                Resource:
                  - '*'
```

Nessa arquivo possui os seguintes recursos:
- API Gateway do tipo REST API
- Lambda Permission que permite consumo pelo API Gateway
- Lambda Function criada apartir do artefato gerado no Code Build.

Com esses arquivos no repositório, podemos realizar um push das alterações para o Code Commit e acompanhar a execução do pipeline:

![Code Pipeline](/assets/images/code-pipeline-webapi-dotnet-core.png "Code Pipeline")

Uma vez finalizado o pipeline, podemos verificar que o API Gateway foi criado:

![Stage Prod do API Gateway](/assets/images/stage-apigateway-webapi-dotnet-core.png "Stage Prod do API Gateway")

Clicando no endpoint fornecido para o stage, temos o seguinte resultado da API:

![Resultado da API](/assets/images/result-apigateway-webapi-dotnet-core.png "Resultado da API")

Nesse ponto temos a aplicação sendo executada em um ambiente serverless com um pipeline automatizado.

Gostou? Tem alguma sugestão ou dúvida? Deixa ai nos comentários!

Segue o link do repositório do projeto:

[Repositório CDK .NET API](https://github.com/alanlviana/cdk-dotnet-api)


