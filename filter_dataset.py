import os
import json
import logging
import yaml
from datetime import datetime
from com_unfi_dataplatform.unfi_common_libraries.logger import get_logger, set_logger
from com_unfi_dataplatform.unfi_common_libraries.s3_utils import get_s3_object
from com_unfi_dataplatform.unfi_common_libraries.common_utils import read_config_file

def get_dataset_sfn_input(dataset_list, dataset, config_bucket, 
                            config_file_prefix, input_execution_dict):
    try:
        logger_obj = get_logger()
        config_object = {}
        for dataset_dict in dataset_list:
            if dataset_dict['dataset'] == dataset:
                config_object = read_config_file(config_bucket,
                    config_file_prefix + dataset_dict['config_file'],
                    json.loads(os.getenv('ssm_dict')))
                break
        
        if config_object['orchestration_type'].upper() == 'FACT':
             
            
            sfn_input =  {
            'execution_name' : config_object['datasource']+"_"+dataset+"_"+datetime.now().strftime("%Y%m%d%H%M%S"),
            'input' : {
                'config_bucket': config_bucket,
                'config_file': config_file_prefix + dataset_dict['config_file'],
                'dataset_name': dataset,
                'input_file_path': input_execution_dict,
                'schema_name': config_object['db_table'].split('.')[0].lower(),
                'table_name': config_object['db_table'].split('.')[1].lower(),
                'upsert_logic_flag': config_object.get('upsert_logic_flag'),
                'insert_pkey': ",".join(config_object.get('primary_keys', [])),
                'date_column': config_object.get('date_column', ''),
                'hist_data_dictionary_list': [str(key.lower())+":"+str(value).strip() for key,value in config_object.get('hist_data_dictionary',{}).items()]
            }
            }
            
        elif config_object['orchestration_type'].upper() == 'DIM':
            
            sfn_input ={
            'execution_name': config_object['datasource']+"_"+dataset+"_"+datetime.now().strftime("%Y%m%d%H%M%S"),
            'input' : {
                'config_bucket': config_bucket,
                'config_file': config_file_prefix + dataset_dict['config_file'],
                'dataset_name': dataset,
                'input_file_path': input_execution_dict,
                'controller_dict': {}
            }
            }
        return config_object['orchestration_type'].upper(),sfn_input
    except Exception as excep_msg:
        logger_obj.error(excep_msg)
        raise excep_msg

def filter_datasets(dataset_list: list, input_execution_file: dict,
                    config_bucket: str, config_file_prefix: str):
    try:
        logger_obj = get_logger()
        logger_obj.info('Reading Input Execution File s3://%s/%s',\
                            input_execution_file.get('bucket'), input_execution_file.get('key'))
        input_execution_dict = yaml.safe_load(get_s3_object(input_execution_file.get('bucket'),\
                            input_execution_file.get('key')))
        fact_sfn_input_list = []
        dim_sfn_input_list = []
        for dataset in input_execution_dict:
            logging.info('Fetching details for Dataset: %s', dataset)
            orch_type, sfn_input = get_dataset_sfn_input(dataset_list, dataset,
                                            config_bucket, config_file_prefix, input_execution_file)
            if orch_type == 'FACT':
                fact_sfn_input_list.append(sfn_input)
            elif orch_type == 'DIM':
                dim_sfn_input_list.append(sfn_input)
        return fact_sfn_input_list, dim_sfn_input_list
    except Exception as excep_msg:
        logger_obj.error(excep_msg)
        raise excep_msg

def lambda_handler(event: dict, context: object):
    try:
        logger_obj = set_logger(context.function_name, 'INFO')
        logger_obj.info('Inside Lambda Handler: %s', context.function_name)
        logger_obj.info('Test Event Received: %s', event)
        dataset_list = yaml.safe_load(get_s3_object(event['config_bucket'], event['config_file']))
        config_file_prefix = event['config_file'].rsplit('/', 1)[0] + '/'
        fact_list, dim_list = filter_datasets(dataset_list,\
                        event.get('input_file_path'), event['config_bucket'], config_file_prefix)
        return {
            'fact': fact_list,
            'dim': dim_list
        }
    except Exception as excep_msg:
        logger_obj.error(excep_msg)
        raise excep_msg
