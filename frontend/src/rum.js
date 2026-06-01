import { AwsRum } from 'aws-rum-web';

export const initCloudWatchRum = () => {
  try {
    const config = {
      sessionSampleRate: 1,
      guestRoleArn: process.env.REACT_APP_AWS_RUM_GUEST_ROLE_ARN,
      identityPoolId: process.env.REACT_APP_AWS_RUM_IDENTITY_POOL_ID,
      endpoint: process.env.REACT_APP_AWS_RUM_ENDPOINT || "https://dataplane.rum.us-east-1.amazonaws.com",
      telemetries: ["errors", "performance", "http"],
      allowCookies: true,
      enableXRay: false
    };

    const APPLICATION_ID = process.env.REACT_APP_AWS_RUM_APPLICATION_ID;
    const APPLICATION_VERSION = '1.0.0';
    const APPLICATION_REGION = process.env.REACT_APP_AWS_RUM_REGION || 'us-east-1';

    if (APPLICATION_ID && config.guestRoleArn && config.identityPoolId) {
      const awsRum = new AwsRum(
        APPLICATION_ID,
        APPLICATION_VERSION,
        APPLICATION_REGION,
        config
      );
      
      console.log("AWS CloudWatch RUM initialized successfully.");
      return awsRum;
    } else {
      console.warn("AWS CloudWatch RUM is not initialized because required environment variables are missing.");
    }
  } catch (error) {
    console.error("Failed to initialize AWS CloudWatch RUM:", error);
  }
  
  return null;
};
