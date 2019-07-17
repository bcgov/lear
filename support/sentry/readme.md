Installation of Sentry Error Monitoring
=========================================


1) Install the Sentry SDK in your porject

	For Python:
		- $ pip install --upgrade sentry-sdk==0.9.5
	
2) From the Senrty.io website:
	
	Goto:
	
	  - https://sentry.io/
	
	( You need to have an account and login to do this. )
	
	  - click "Create Project" to create a project <key>.
	
	
3) To capture exceptions, insert into your code using the key provided by your Sentry project:
	
	- import sentry_sdk
	
	- sentry_sdk.init("https://<key>@sentry.io/<project>")


4) For Vue:
	- $ npm install @sentry/browser
	
	
Sentry will now intercept all standard exceptions.


Custom Exceptions and messages
------------------------------

1) For custom Exceptions add these lines of code whenever you define a new exception.

    Import:		
    
	- from sentry_sdk import capture_exception
	
    Inside the custom exception	handler add:    
    
    	- capture_exception(e)


2) For messages:
    
    Import:
    
    	- from sentry_sdk import capture_message
    	
    Inside the code add:        
    
    	- capture_msessage("The message text")




	
	