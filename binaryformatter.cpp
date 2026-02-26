private static T ReadCache<T>(string storeFileName, bool mustExist)
        {
            new SecurityPermission(SecurityPermissionFlag.SerializationFormatter).Demand();
            new FileIOPermission(FileIOPermissionAccess.Read | FileIOPermissionAccess.PathDiscovery, storeFileName).Assert();
            BinaryFormatter binaryFormatter = new BinaryFormatter();
            T t = default(T);
            if (File.Exists(storeFileName))
            {
                for (int i = 0; i < 4; i++)
                {
                    try
                    {
                        using (Stream stream = File.OpenRead(storeFileName))
                        {
                            if (stream.Length < 12L)
                            {
                                throw new InvalidOperationException(string.Format(CultureInfo.CurrentCulture, Res.DeployedAddInsFileCorrupted, new object[] { storeFileName }));
                            }
                            BinaryReader binaryReader = new BinaryReader(stream);
                            int num = binaryReader.ReadInt32();
                            long num2 = binaryReader.ReadInt64();
                            try
                            {
                                t = (T)((object)binaryFormatter.Deserialize(stream));
                            }
                            catch (Exception ex)
                            {
                                throw new InvalidOperationException(string.Format(CultureInfo.CurrentCulture, Res.CantDeserializeData, new object[] { storeFileName }), ex);
                            }
                        }
                        break;
                    }
                    catch (IOException ex2)
                    {
                        if (Marshal.GetHRForException(ex2) != -2147024864)
                        {
                            throw;
                        }
                        Thread.Sleep(500);
                    }
                }
                return t;
            }
            if (mustExist)
            {
                throw new InvalidOperationException(string.Format(CultureInfo.CurrentCulture, Res.CantFindDeployedAddInsFile, new object[] { storeFileName }));
            }
            return t;
        }
