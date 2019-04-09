from flask_restful import Resource
from flask import request, json
from models.slr import slr
from models.tokens import TokensModel
import datetime
import time
from schema import Schema, And, Use, SchemaError, SchemaForbiddenKeyError, SchemaMissingKeyError,\
    SchemaUnexpectedTypeError, SchemaWrongKeyError

UPLOAD_FOLDER = '.'
ALLOWED_EXTENSIONS = set(['json'])


class ImportCodes(Resource):
    def __init__(self):
        self.slr = slr("", "", "")
        pass

    def __del__(self):
        del(self.slr)
        pass

    def post(self):
        # First validate incoming file and JSON
        result = ImportCodes.validate_json(request)
        if result['code'] != 201:
            return {'message': result['message']}, result['code']

        # Move further if we got validated_json back
        validated_json = result['validated_json']
        if validated_json is not None:
            print("==>> Now printing validated JSON...")
            print(validated_json)
        else:
            return {'message': 'NOT able to validate JSON for unknown reason!'}, 500

        # If everything is ok, fetch uuid
        uuid = validated_json['registration-uuid']

        # Now insert/update db based on codes_type
        if result['codes_type'] == "request_codes":
            update_result = ImportCodes.update_req_codes_slr(validated_json)
            # if update_result['code'] != 201:
            #     return {'message': result['message'], 'uuid': uuid, 'codes_type': result['codes_type']}, result['code']
        elif result['codes_type'] == "auth_codes":
            update_result = ImportCodes.update_auth_codes_slr(validated_json)
            # if update_result['code'] != 201:
            #     return {'message': result['message'], 'uuid': uuid, 'codes_type': result['codes_type']}, result['code']
        else:
            return {'message': 'NOT able to detect codes_type for unknown reason!'}, 500

        return {'message': result['message'], 'uuid': uuid, 'codes_type': result['codes_type']}, update_result['code']

    @classmethod
    def update_req_codes_slr(cls, validated_json):
        # s = slr("", "", "")
        # Start extracting required fields from json
        uuid = validated_json['registration-uuid']
        registration_name = validated_json['registration-name']

        # First check if devices with this UUID already exists
        try:
            rows_slr = TokensModel.find_by_uuid(uuid, "slr_request_code_tbl")
            rows = TokensModel.find_by_uuid(uuid, "device_store")
        except Exception as e:
            print(e)
            return {"message": "Data search operation failed!", 'code': 500}

        if rows_slr:
            # Changed to 200 from 400 on UI Dev team request
            print("==>> UUID already exists in slr_request_code_tbl...")
            return {"message": "Registration request with this UUID already exists!", 'code': 200}

        if rows:
            # Changed to 200 from 400 on UI Dev team request
            print("==>> UUID already exists in device_store...")
            return {"message": "Registration request with this UUID already exists!", 'code': 200}

        # Creat update_slr_reqcode_table_dict
        insert_slr_reqcode_table_list = []
        insert_device_store_table_list = []
        insert_upload_info_store_table_list = []

        for device in validated_json['devices']:
            # Traverse through validated_json dictionary and create a list of flat key-value pair dict
            each_device_reqcode_dict = {}
            each_device_store_dict = {}
            each_device_upload_info_store_dict = {}
            # Initialize lic_count_str & lic_ent_tag_str
            lic_count_str, lic_ent_tag_str = "", ""
            # Prepare fields for slr_request_code_tbl
            each_device_reqcode_dict['uuid'] = uuid
            each_device_reqcode_dict['ipaddr'] = device['device-uuid']
            each_device_reqcode_dict['step1'] = device['step1']
            each_device_reqcode_dict['step2'] = "NS"
            each_device_reqcode_dict['step3'] = "NS"
            each_device_reqcode_dict['authz_req_code'] = device['request-code']
            each_device_reqcode_dict['authz_response_code'] = ""
            each_device_reqcode_dict['license'] = ""
            for license in device['licenses']:
                print("\n\n")
                print("**** Printing license sub-json...")
                print(license)
                lic_count_str += license['license-count'] + " "
                lic_ent_tag_str += license['license-entitlement-tag'] + " "
            each_device_reqcode_dict['license_count'] = lic_count_str.strip()
            each_device_reqcode_dict['license_entitlement_tag'] = lic_ent_tag_str.strip()
            print("\n\n")
            print("**** Importing license count...")
            print(each_device_reqcode_dict['license_count'])
            print("**** Importing license cent tag...")
            print(each_device_reqcode_dict['license_entitlement_tag'])
            print("\n\n")
            each_device_reqcode_dict['tftp_server_ip'] = ""
            each_device_reqcode_dict['tftp_server_path'] = ""
            each_device_reqcode_dict['device_uuid'] = device['device-uuid']

            # Prepare fields for device_store
            each_device_store_dict['uuid'] = uuid
            each_device_store_dict['ipaddr'] = device['device-uuid']
            each_device_store_dict['username'] = "NA"
            each_device_store_dict['password'] = "NA"
            each_device_store_dict['sa_name'] = device['sa-name']
            each_device_store_dict['va_name'] = device['va-name']
            each_device_store_dict['domain'] = device['domain']
            each_device_store_dict['device_uuid'] = device['device-uuid']
            
            # Prepare fields for upload_info_store
            each_device_upload_info_store_dict['uuid'] = uuid
            each_device_upload_info_store_dict['userid'] = "NA"
            each_device_upload_info_store_dict['filename'] = registration_name
            each_device_upload_info_store_dict['type'] = "slr"
            each_device_upload_info_store_dict['timestamp'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
            # each_device_upload_info_store_dict['status'] = "S2c"
            each_device_upload_info_store_dict['status'] = "S2ci"

            # Now add each_device_reqcode_dict to update_slr_reqcode_table_list
            insert_slr_reqcode_table_list.append(each_device_reqcode_dict)

            # Now add each_device_store_dict to update_device_store_table_list
            insert_device_store_table_list.append(each_device_store_dict)

            # Now add each_device_upload_info_store_dict to insert_upload_info_store_table_list
            insert_upload_info_store_table_list.append(each_device_upload_info_store_dict)

        # Now print list of flat key-value pair dict - update_slr_reqcode_table_list
        print("==>> Printing update_slr_reqcode_table_list before inserting into slr_request_code_tbl...")
        print(insert_slr_reqcode_table_list)

        # Now print list of flat key-value pair dict - update_device_store_table_list
        print("==>> Printing update_device_store_table_list before inserting into device_store...")
        print(insert_device_store_table_list)

        # Now print list of flat key-value pair dict - insert_upload_info_store_table_list
        print("==>> Printing insert_upload_info_store_table_list before inserting into upload_info_store")
        print(insert_upload_info_store_table_list)

        try:
            TokensModel.insert_slr(uuid, insert_slr_reqcode_table_list, "slr_request_code_tbl")
            print("==>> Now printing slr_request_code_tbl after updateing request_codes...")
            if TokensModel.find_by_uuid(uuid, "slr_request_code_tbl"):
                print("==>> Done printing slr_request_code_tbl")
        except Exception as e:
            print("==>> Printig exception while inserting data into slr_request_code_tbl...")
            print(e)
            return {'message': "Data insert operation slr_request_code_tbl failed!", 'code': 500}

        try:
            TokensModel.insert(uuid, insert_device_store_table_list, "device_store")
            print("==>> Now printing device_store after updating sa, va, domain...")
            if TokensModel.find_by_uuid(uuid, "device_store"):
                print("==>> Done printing device_store")
        except Exception as e:
            print("==>> Printig exception while inserting data into device_store...")
            print(e)
            return {'message': "Data insert operation device_store failed!", 'code': 500}

        try:
            TokensModel.insert(uuid, insert_upload_info_store_table_list, "upload_info_store")
            print("==>> Now printing upload_info_store after updating registration-name, status...")
            if TokensModel.find_by_uuid(uuid, "upload_info_store"):
                print("==>> Done printing upload_info_store")
        except Exception as e:
            print("==>> Printig exception while inserting data into upload_info_store...")
            print(e)
            return {'message': "Data insert operation device_store failed!", 'code': 500}

        # Finally return success - 201
        return {'message': "Tables successfully updated!", 'code': 201}


        # Initializing req_codes to "" string, it is already done when table is initialized
        # Not sure if this is needed
        # s.update_req_token("slr_request_code_tbl", uuid, device_ip, "")



        # Update req_token, license tag and license count
        # s.update_req_token("slr_request_code_tbl", uuid, device_ip, req_token)
        # s.update_entitlement_tag("slr_request_code_tbl", uuid, device_ip, result)
        # s.update_license_count("slr_request_code_tbl", uuid, device_ip, result_lic_count)

        #update status
        # s.update_status("slr_request_code_tbl", uuid, device_ip, step_status, "step1")

        # response_update = {}
        # response_update['status'] = "S2cx"
        # TokensModel.update(uuid, response_update, "upload_info_store")

    @classmethod
    def update_auth_codes_slr(cls, validated_json):
        s = slr("", "", "")
        # Start extracting required fields from json
        uuid = validated_json['registration-uuid']
        # registration_name = validated_json['registration-name']

        # First check if devices with this UUID already exists
        try:
            rows_slr = TokensModel.find_by_uuid(uuid, "slr_request_code_tbl")
            rows = TokensModel.find_by_uuid(uuid, "device_store")
        except Exception as e:
            print(e)
            return {"message": "Data search operation failed!", 'code': 500}

        if not rows_slr:
            # Changed to 200 from 400 on UI Dev team request
            print("==>> UUID doesn't exists in slr_request_code_tbl...")
            return {"message": "Registration request with this UUID doesn't exists!", 'code': 200}

        if not rows:
            # Changed to 200 from 400 on UI Dev team request
            print("==>> UUID doesn't exists in device_store...")
            return {"message": "Registration request with this UUID doesn't exists!", 'code': 200}

        # Prepare fields for upload_info_store
        upload_info_store_dict = {}
        upload_info_store_dict['status'] = "S3si"
        try:
            TokensModel.update(uuid, upload_info_store_dict, "upload_info_store")
        except Exception as e:
            print(e)
            return {'message': "Status update operation upload_info_store failed!", 'code': 500}

        for device in validated_json['devices']:

            # Update status for step2 (Auth-Code generation) for each device
            try:
                s.update_status_device_uuid("slr_request_code_tbl", uuid, device['device-uuid'],
                                            device['step2'], 'step2')
            except Exception as e:
                print("++>> Not able to update step2 status in slr_request_code_tbl...")
                print(e)

            # Update Auth-Code for each device
            try:
                s.update_authz_response_code_device_uuid("slr_request_code_tbl", uuid, device['device-uuid'],
                                                         device['auth-code'])
            except Exception as e:
                print("++>> Not able to update Auth-Code in slr_request_code_tbl...")
                print(e)

        # Prepare fields for upload_info_store
        upload_info_store_dict['status'] = "S3ci"
        # We are updating timestamp only when step2 is complete
        upload_info_store_dict['timestamp'] = datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')

        try:
            TokensModel.update(uuid, upload_info_store_dict, "upload_info_store")
        except Exception as e:
            print(e)
            return {'message': "Status update operation slr_request_code_tbl failed!", 'code': 500}

        # Finally return success - 201
        return {'message': "Tables successfully updated!", 'code': 201}

    @classmethod
    def validate_json(cls, request):
        # print(request.files.to_dict()['file'])
        print(request.headers)
        validated_codes_json = None
        codes_type = None
        if 'file' not in request.files:
            # Changed to 200 from 400 on UI Dev team request
            return {'message': "No File in the request!", 'code': 200, 'validated_json': validated_codes_json,
                    'codes_type': codes_type}
        codes_data = request.files['file']

        if codes_data.filename == '':
            # Changed to 200 from 400 on UI Dev team request
            return {'message': "No File selected!", 'code': 200, 'validated_json': validated_codes_json,
                    'codes_type': codes_type}

        if not ImportCodes.allowed_file(codes_data.filename):
            # Changed to 200 from 400 on UI Dev team request
            return {'message': "File type not allowed! Only JSON files are allowed!", 'code': 200,
                    'validated_json': validated_codes_json, 'codes_type': codes_type}

        try:
            codes_json = json.loads(codes_data.read())
            print("Now printing request_code_json ...")
            print(codes_json)
            codes_type = codes_json['slr-data-export-type']
        except ValueError:
            # Changed to 200 from 400 on UI Dev team request
            return {'message': "Reading file and decoding JSON has failed. Please check your JSON file syntax!",
                    'code': 200, 'validated_json': validated_codes_json, 'codes_type': codes_type}

        if codes_type == "request_codes":
            # request_codes
            request_codes_schema = Schema({'registration-name': And(str, len),
                                           'slr-data-export-type':  And(str, len),
                                           'registration-uuid': And(str, len),
                                           'exported-on': And(str, len),
                                           'total-devices': And(Use(int), lambda n: 1 <= n <= 100),
                                           'devices-with-success': And(Use(int), lambda n: 0 <= n <= 100),
                                           'devices': [{'device-uuid': And(str, len),
                                                        'sa-name': And(str, len),
                                                        'va-name': And(str, len),
                                                        'domain': And(str, len),
                                                        'request-code': And(str, len),
                                                        'step1': And(str, len),
                                                        'licenses': [{'license-entitlement-tag': And(str, len),
                                                                      'license-count': And(str, len)}]
                                                        }]
                                           })
            try:
                validated_codes_json = request_codes_schema.validate(codes_json)
            except SchemaError as e:
                print("==>> Printing Schema Validation Error Message...")
                print(e)
                # Changed to 200 from 400 on UI Dev team request
                return {'message': "JSON validation has failed, please check file contents: " + str(e), 'code': 200,
                        'validated_json': validated_codes_json, 'codes_type': codes_type}
        elif codes_type == "auth_codes":
            # auth_codes
            auth_codes_schema = Schema({'registration-name': And(str, len),
                                        'slr-data-export-type':  And(str, len),
                                        'registration-uuid': And(str, len),
                                        'exported-on': And(str, len),
                                        'total-devices': And(Use(int), lambda n: 1 <= n <= 100),
                                        'devices-with-success': And(Use(int), lambda n: 0 <= n <= 100),
                                        'devices': [{'device-uuid': And(str, len),
                                                     'auth-code': And(str, len),
                                                     'step2': And(str, len)
                                                     }]
                                        })
            try:
                validated_codes_json = auth_codes_schema.validate(codes_json)
            except SchemaError as e:
                print("==>> Printing Schema Validation Error Message...")
                print(e)
                # Changed to 200 from 400 on UI Dev team request
                return {'message': "JSON validation has failed, please check file contents: " + str(e), 'code': 200,
                        'validated_json': validated_codes_json, 'codes_type': codes_type}
        else:
            # Changed to 200 from 400 on UI Dev team request
            return {'message': "slr-data-export-type field in JSON doesn't NOT contain expected value!", 'code': 200,
                    'validated_json': validated_codes_json, 'codes_type': codes_type}
        return {'message': "File successfully uploaded!", 'code': 201, 'validated_json': validated_codes_json,
                'codes_type': codes_type}

    @classmethod
    def allowed_file(cls, filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
