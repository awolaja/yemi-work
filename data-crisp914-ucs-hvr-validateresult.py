import json
from com_unfi_dataplatform.unfi_common_libraries.logger import get_logger, set_logger

def lambda_handler(event, context):
    try:
        logger_obj = set_logger(context.function_name, 'INFO')
        logger_obj.info('Inisde Function %s', context.function_name)
        logger_obj.info('Event received: %s', event)

        # Validate the result received from the Map state
        # Expected event type is list
        if isinstance(event, list):
            error_sfn_list = []
            for datasets_execution_detail_list in event:
                # Expected 2 lists of lists 1: Facts 2: Dimennsions
                for dataset_execution_dict in datasets_execution_detail_list:
                    # pass state
                    if 'status' in dataset_execution_dict:
                        if dataset_execution_dict['status'].upper() == 'SUCCEEDED':
                            logger_obj.info('Stepfunction %s status is successfull',\
                                dataset_execution_dict.get('ExecutionArn'))
                        elif dataset_execution_dict['status'].upper() in ['FAILED', 'ABORTED', 'TIMED_OUT']:
                            logger_obj.info('Stepfunction %s status is %s',\
                                dataset_execution_dict.get('ExecutionArn'),\
                                dataset_execution_dict['status'].upper())
                            error_sfn_list.append(dataset_execution_dict.get('ExecutionArn'))
                    elif 'Error' in dataset_execution_dict:
                        cause_dict = json.loads(dataset_execution_dict['Cause'])
                        if 'ExecutionArn' in cause_dict:
                            logger_obj.info('Stepfunction %s status is %s',\
                                    cause_dict.get('ExecutionArn'),\
                                    cause_dict['Status'].upper())
                            error_sfn_list.append(cause_dict.get('ExecutionArn'))
                        else:
                            error_sfn_list.append(dataset_execution_dict)
            if error_sfn_list != []:
                raise Exception('Some SFN executions have failed. Details: {}'\
                    .format(error_sfn_list))
            else:
                logger_obj.info('All executions were successful. Exiting function')
        else:
            raise Exception('Not en expected input Expected a list type: {}'.format(event))
    except Exception as excep_msg:
        raise excep_msg    