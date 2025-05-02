BEGIN

SET ANSI_NULLS ON

SET QUOTED_IDENTIFIER ON

CREATE TABLE [dbo].[LogsExecutor](
	[RequestId] [uniqueidentifier] NULL,
	[Mensagem] [nvarchar](max) NOT NULL,
	[Data] [datetime] NOT NULL
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

CREATE TABLE [dbo].[Notebook](
	[NotebookName] [nvarchar](200) NOT NULL,
	[Version] [nvarchar](10) NOT NULL,
	[FilePath] [nvarchar](4000) NOT NULL,
	[RequiredParams] [nvarchar](max) NOT NULL,
	[OutputExt] [nvarchar](10) NOT NULL,
 CONSTRAINT [PK_Notebook] PRIMARY KEY CLUSTERED 
(
	[NotebookName] ASC,
	[Version] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]


CREATE TABLE [dbo].[Pipelines](
	[Id] [uniqueidentifier] NOT NULL,
	[Name] [nvarchar](255) NOT NULL,
	[Description] [nvarchar](max) NULL,
	[CreatedAt] [datetime2](7) NOT NULL,
PRIMARY KEY CLUSTERED 
(
	[Id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

ALTER TABLE [dbo].[Pipelines] ADD  DEFAULT (sysutcdatetime()) FOR [CreatedAt]

CREATE TABLE [dbo].[PipelineParameters](
	[Id] [uniqueidentifier] NOT NULL,
	[PipelineId] [uniqueidentifier] NOT NULL,
	[Name] [nvarchar](255) NOT NULL,
	[Type] [nvarchar](50) NOT NULL,
	[Value] [nvarchar](max) NULL,
PRIMARY KEY CLUSTERED 
(
	[Id] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

ALTER TABLE [dbo].[PipelineParameters]  WITH CHECK ADD  CONSTRAINT [FK_PipelineParameters_Pipelines] FOREIGN KEY([PipelineId])
REFERENCES [dbo].[Pipelines] ([Id])
ON DELETE CASCADE

ALTER TABLE [dbo].[PipelineParameters] CHECK CONSTRAINT [FK_PipelineParameters_Pipelines]

CREATE TABLE [dbo].[Tasks](
	[RequestId] [uniqueidentifier] NOT NULL,
	[NotebookName] [nvarchar](200) NULL,
	[Version] [nvarchar](10) NULL,
	[Params] [nvarchar](max) NULL,
	[Status] [nvarchar](30) NULL,
	[RetryCount] [int] NULL,
	[CreatedAt] [datetime] NULL,
	[StartedAt] [datetime] NULL,
	[FinishedAt] [datetime] NULL,
	[OutputType] [nvarchar](10) NULL,
	[OutputPath] [nvarchar](4000) NULL,
	[Error] [nvarchar](max) NULL,
PRIMARY KEY CLUSTERED 
(
	[RequestId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY] TEXTIMAGE_ON [PRIMARY]

ALTER TABLE [dbo].[Tasks] ADD  DEFAULT ((0)) FOR [RetryCount]

ALTER TABLE [dbo].[Tasks] ADD  DEFAULT (getdate()) FOR [CreatedAt]

-- Execute no SQL Server Management Studio (SSMS)
CREATE LOGIN pipeline_user WITH PASSWORD = 'SenhaSegura123!';
CREATE USER pipeline_user FOR LOGIN pipeline_user;
-- conceda permissões adequadas, por exemplo:
ALTER ROLE db_datareader ADD MEMBER pipeline_user;
ALTER ROLE db_datawriter ADD MEMBER pipeline_user;


END
